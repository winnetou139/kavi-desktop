"""Read-only reader for the canonical KAVI Vault.

The vault is canonical organizational knowledge (D-005). This reader never
writes, never synchronizes, and never treats a vault note as operational state.
"""

from __future__ import annotations

import os
import pathlib
import re
from typing import Any

DEFAULT_VAULT_CANDIDATES = (
    r"C:\Users\abdul.kausar\Desktop\AI Workspace\PCOS\KAVI_Vault_v0.1\KAVI_Vault_v0.1",
)

UNKNOWN_TEXT = "UNKNOWN / NOT STATED IN THE RECORD"

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")


def resolve_vault_path(explicit: str | None = None) -> pathlib.Path | None:
    if explicit:
        candidate = pathlib.Path(explicit)
        return candidate if candidate.is_dir() else None
    env = os.environ.get("KAVI_VAULT_PATH")
    if env and pathlib.Path(env).is_dir():
        return pathlib.Path(env)
    for candidate in DEFAULT_VAULT_CANDIDATES:
        path = pathlib.Path(candidate)
        if path.is_dir():
            return path
    return None


def _strip_markdown(value: str) -> str:
    """Remove inline markdown emphasis and code ticks, keeping the words.

    Emphasis in the register marks reviewer corrections; the emphasis itself is
    presentation, but the text it wraps is meaning and must never be lost.
    """
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", value)
    value = value.replace("`", "")
    value = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m.group(1).split("|")[0], value)
    return " ".join(value.split()).strip()


def _parse_frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.strip().startswith("-"):
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _first_paragraph(text: str) -> str:
    body = _FRONTMATTER.sub("", text)
    for block in body.split("\n\n"):
        cleaned = block.strip()
        if not cleaned or cleaned.startswith("#") or cleaned.startswith("|"):
            continue
        cleaned = _WIKILINK.sub(lambda m: m.group(1).split("|")[0], cleaned)
        return " ".join(cleaned.split())[:400]
    return ""


class VaultReader:
    """Read-only navigation over the vault."""

    def __init__(self, root: pathlib.Path | str | None = None) -> None:
        resolved = resolve_vault_path(str(root) if root else None)
        self.root = resolved
        self._index: list[dict[str, Any]] | None = None

    @property
    def available(self) -> bool:
        return self.root is not None and self.root.is_dir()

    def status(self) -> dict[str, Any]:
        if not self.available:
            return {
                "available": False,
                "path": "",
                "note_count": 0,
                "access": "READ ONLY",
                "sync": "NOT CONNECTED",
                "detail": "Canonical vault not found. Set KAVI_VAULT_PATH or pass --vault.",
            }
        notes = self.index()
        return {
            "available": True,
            "path": str(self.root),
            "note_count": len(notes),
            "access": "READ ONLY",
            "sync": "NOT CONNECTED",
            "detail": "Vault is canonical organizational knowledge (D-005). No writes, no sync in v0.1.",
        }

    def index(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        if self._index is not None and not refresh:
            return self._index
        if not self.available:
            self._index = []
            return self._index
        assert self.root is not None
        rows: list[dict[str, Any]] = []
        for path in sorted(self.root.rglob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            front = _parse_frontmatter(text)
            relative = path.relative_to(self.root)
            section = relative.parts[0] if len(relative.parts) > 1 else "(root)"
            rows.append(
                {
                    "id": str(relative).replace("\\", "/"),
                    "title": front.get("title") or path.stem,
                    "section": section,
                    "path": str(relative).replace("\\", "/"),
                    "doc_type": front.get("type", ""),
                    "document_state": (front.get("status", "active") or "active").upper(),
                    "summary": _first_paragraph(text),
                    "origin": "LOCAL",
                }
            )
        self._index = rows
        return rows

    def sections(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for note in self.index():
            counts[note["section"]] = counts.get(note["section"], 0) + 1
        return [
            {"section": name, "count": count}
            for name, count in sorted(counts.items())
        ]

    def read(self, relative_path: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        assert self.root is not None
        if ".." in relative_path or pathlib.PurePath(relative_path).is_absolute():
            return None
        target = (self.root / relative_path).resolve()
        try:
            target.relative_to(self.root.resolve())
        except ValueError:
            return None
        if not target.is_file() or target.suffix.lower() != ".md":
            return None
        text = target.read_text(encoding="utf-8")
        front = _parse_frontmatter(text)
        return {
            "path": relative_path,
            "title": front.get("title") or target.stem,
            "doc_type": front.get("type", ""),
            "document_state": (front.get("status", "active") or "active").upper(),
            "content": text,
            "access": "READ ONLY",
            "links": self.outgoing_links(relative_path, text),
            "backlinks": self.backlinks(target.stem),
        }

    def outgoing_links(self, relative_path: str, text: str | None = None) -> list[dict[str, Any]]:
        """Wikilinks in a note, resolved to real vault paths where possible."""
        if not self.available:
            return []
        assert self.root is not None
        if text is None:
            target = (self.root / relative_path)
            if not target.is_file():
                return []
            text = target.read_text(encoding="utf-8")
        prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        prose = re.sub(r"`[^`]*`", "", prose)
        by_stem = {note["title"]: note for note in self.index()}
        by_basename = {
            pathlib.PurePath(note["path"]).stem: note for note in self.index()
        }
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for raw in _WIKILINK.findall(prose):
            name = raw.split("|")[0].split("#")[0].strip()
            if not name or name in seen:
                continue
            seen.add(name)
            stem = pathlib.PurePath(name.replace("\\", "/")).stem
            match = by_basename.get(stem) or by_stem.get(name)
            out.append({
                "name": name,
                "path": match["path"] if match else "",
                "resolved": bool(match),
            })
        return out

    def backlinks(self, note_stem: str) -> list[dict[str, Any]]:
        """Notes that link to this one."""
        if not self.available:
            return []
        assert self.root is not None
        needle = note_stem.lower()
        out: list[dict[str, Any]] = []
        for note in self.index():
            path = self.root / note["path"]
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for raw in _WIKILINK.findall(text):
                name = raw.split("|")[0].split("#")[0].strip()
                if pathlib.PurePath(name.replace("\\", "/")).stem.lower() == needle:
                    out.append({"title": note["title"], "path": note["path"]})
                    break
        return out

    # ------------------------------------------------------------ decisions

    def programme(self) -> dict[str, Any]:
        """The KAVI programme roadmap, read from the vault.

        The Founder asked where his own plan stands. That plan is a vault
        note, so it is read from there rather than restated -- the same
        discipline applied to decisions and evidence.

        Returns every field UNKNOWN when the note is absent. A programme
        status that guesses is worse than one that admits it cannot see.
        """
        blank = {
            "source": "CANONICAL VAULT",
            "available": False,
            "access": "NOT FOUND",
            "phases": [],
            "current_phase": UNKNOWN_TEXT,
            "current_scope": UNKNOWN_TEXT,
            "counts": {},
            "detail": ("KAVI Program Roadmap.md is not in the vault, so the "
                       "programme phase is UNKNOWN."),
        }
        if self.root is None:
            return blank
        note = self.root / "02_VENTURE_SYSTEM" / "KAVI Program Roadmap.md"
        if not note.is_file():
            return blank
        try:
            text = note.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return blank

        block = text.split("## Program phases", 1)
        if len(block) < 2:
            return blank
        body = block[1].split("\n## ", 1)[0]

        phases: list[dict[str, str]] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3 or cells[0].lower() == "phase":
                continue
            phases.append({
                "id": _plain_cell(cells[0]),
                "scope": _plain_cell(cells[1]),
                "state": _programme_state(cells[2]),
                "origin": "VAULT",
            })

        counts: dict[str, int] = {}
        for phase in phases:
            counts[phase["state"]] = counts.get(phase["state"], 0) + 1
        current = next((p for p in phases if p["state"] == "IN PROGRESS"), None)
        blocked = [p["id"] for p in phases if p["state"] == "BLOCKED"]

        return {
            "source": "CANONICAL VAULT",
            "available": True,
            "access": "READ ONLY",
            "phases": phases,
            "phase_count": len(phases),
            "counts": counts,
            "current_phase": current["id"] if current else UNKNOWN_TEXT,
            "current_scope": current["scope"] if current else UNKNOWN_TEXT,
            "blocked": blocked,
            "detail": ("Programme phases are read from "
                       "02_VENTURE_SYSTEM/KAVI Program Roadmap.md. The cockpit "
                       "never writes to the vault and may not advance a phase."),
        }

    def decisions(self) -> list[dict[str, Any]]:
        """Read the canonical decision records from 08_DECISIONS/.

        Decisions are organizational knowledge, so the vault owns them (D-005).
        The desktop reads them and never writes one. Anything the record does
        not state is returned empty rather than guessed — a decision record is
        exactly the place where invention is most damaging.
        """
        if not self.available:
            return []
        assert self.root is not None
        folder = self.root / "08_DECISIONS"
        if not folder.is_dir():
            return []

        out: list[dict[str, Any]] = []
        for path in sorted(folder.glob("*.md")):
            if path.stem.lower().startswith("decision log"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            record = self._parse_decision(text, path)
            if record:
                out.append(record)
        out.sort(key=lambda row: row["id"])
        return out

    def _parse_decision(self, text: str, path: pathlib.Path) -> dict[str, Any] | None:
        front = _parse_frontmatter(text)
        body = _FRONTMATTER.sub("", text)

        bold = dict(re.findall(r"\*\*(.+?):\*\*\s*(.*)", body))
        identifier = (bold.get("Decision ID") or "").strip()
        if not identifier:
            match = re.match(r"(D-\d+)", path.stem)
            identifier = match.group(1) if match else ""
        if not identifier:
            return None

        def section(name: str) -> str:
            match = re.search(
                rf"^##\s+{re.escape(name)}\s*\n(.*?)(?=^##\s|\Z)",
                body, re.MULTILINE | re.DOTALL,
            )
            if not match:
                return ""
            return " ".join(match.group(1).split()).strip()

        title = (front.get("title") or "").strip()
        if " — " in title:
            title = title.split(" — ", 1)[1]
        if not title:
            heading = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            title = heading.group(1).replace("Decision — ", "").strip() if heading else path.stem

        state = (bold.get("Decision State") or "").strip().upper()
        em_dash_is_empty = lambda value: "" if value.strip() in ("—", "-", "") else value.strip()

        return {
            "id": identifier,
            "title": title,
            "state": state or "UNKNOWN",
            "owner_actor_id": em_dash_is_empty(bold.get("Owner", "")),
            "approver_actor_id": em_dash_is_empty(bold.get("Approver", "")),
            "date": em_dash_is_empty(bold.get("Date", "")),
            "context": section("Context"),
            "decision": section("Decision"),
            "rationale": section("Why"),
            "evidence_ids": section("Evidence basis"),
            "consequences": section("Consequences"),
            "reversible": section("Reversible?") or UNKNOWN_TEXT,
            "supersedes": em_dash_is_empty(bold.get("Supersedes", "")),
            "review_date": section("Review date"),
            "alternatives": section("Alternatives considered"),
            "source_path": str(path.relative_to(self.root)),
            "origin": "VAULT",
        }

    # ------------------------------------------------------------- evidence

    EVIDENCE_REGISTER = "07_RESEARCH/OBJ-2026-001 Evidence Register.md"

    def evidence(self, relative_path: str | None = None) -> list[dict[str, Any]]:
        """Read the canonical evidence register.

        Claims are organizational knowledge owned by the vault. Each row keeps
        its real ID, classification, confidence, and — critically — its recorded
        contradiction or limitation. Contradictions are never dropped: the
        Evidence and Review Contract requires them to survive to the reader.
        """
        if not self.available:
            return []
        assert self.root is not None
        target = self.root / (relative_path or self.EVIDENCE_REGISTER)
        if not target.is_file():
            return []
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        source_path = str(target.relative_to(self.root))
        rows: list[dict[str, Any]] = []
        section = ""
        headers: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()

            heading = re.match(r"^##\s+(.+)$", stripped)
            if heading:
                section = heading.group(1).strip()
                headers = []
                continue

            if not stripped.startswith("|"):
                continue

            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not cells:
                continue

            # A header row redefines the columns for the table that follows;
            # section G uses a shorter column set than the others.
            if cells[0] == "ID":
                headers = [c.lower() for c in cells]
                continue
            if set(stripped) <= set("|-: "):
                continue
            if not headers or not re.match(r"^CLM-\d+$", cells[0]):
                continue

            row = dict(zip(headers, cells))
            rows.append(self._evidence_row(row, section, source_path))

        return rows

    def _evidence_row(
        self, row: dict[str, str], section: str, source_path: str
    ) -> dict[str, Any]:
        def field(*names: str) -> str:
            for name in names:
                value = row.get(name, "").strip()
                if value and value not in ("—", "-"):
                    return _strip_markdown(value)
            return ""

        classification = field("class").upper() or "UNKNOWN"
        return {
            "id": field("id"),
            "claim": field("claim"),
            "classification": classification,
            "source": field("source"),
            "source_date": field("source date"),
            "kind": field("kind"),
            "locator": field("locator"),
            "access_date": field("access date"),
            "confidence": field("confidence").upper(),
            "freshness": field("freshness"),
            # Whatever the column is called, the caveat must survive.
            "contradiction": field(
                "contradiction / limitation",
                "why it threatens the recommendation",
                "limitation",
                "note",
            ),
            "section": section,
            "objective_id": "OBJ-2026-001",
            "source_path": source_path,
            "origin": "VAULT",
        }

    def evidence_status(self) -> dict[str, Any]:
        """Where the evidence register is read from, and its stated scope."""
        if not self.available:
            return {
                "source": "VAULT NOT AVAILABLE",
                "path": "",
                "access": "READ ONLY",
                "claim_count": 0,
                "detail": (
                    "The canonical vault could not be read, so no claim is shown. "
                    "Nothing is substituted in its place."
                ),
            }
        assert self.root is not None
        claims = self.evidence()
        target = self.root / self.EVIDENCE_REGISTER
        scope = ""
        if target.is_file():
            text = target.read_text(encoding="utf-8")
            match = re.search(r"\*\*Scope limit:\*\*\s*(.+)", text)
            if match:
                scope = _strip_markdown(match.group(1).strip())
        return {
            "source": "CANONICAL VAULT" if claims else "REGISTER NOT FOUND",
            "path": self.EVIDENCE_REGISTER,
            "access": "READ ONLY",
            "claim_count": len(claims),
            "scope_limit": scope,
            "detail": (
                "Claims are read from the canonical evidence register. The desktop "
                "never authors a claim, and never drops a recorded contradiction."
            ),
        }

    def search(self, query: str, *, limit: int = 60) -> list[dict[str, Any]]:
        """Full-text search across canonical notes, with a matching excerpt."""
        if not self.available or not query.strip():
            return []
        assert self.root is not None
        needle = query.strip().lower()
        results: list[dict[str, Any]] = []
        for note in self.index():
            path = self.root / note["path"]
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            haystack = text.lower()
            in_title = needle in note["title"].lower()
            hits = haystack.count(needle)
            if not hits and not in_title:
                continue
            excerpt = ""
            position = haystack.find(needle)
            if position >= 0:
                start = max(0, position - 90)
                excerpt = " ".join(text[start:position + 160].split())
            results.append({
                **note,
                "hits": hits,
                "in_title": in_title,
                "excerpt": excerpt,
            })
        results.sort(key=lambda row: (not row["in_title"], -row["hits"]))
        return results[:limit]


def _plain_cell(cell: str) -> str:
    """Strip markdown emphasis and links from a table cell."""
    import re as _re
    cell = _re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell)
    return cell.replace("**", "").replace("*", "").replace("`", "").strip()


def _programme_state(cell: str) -> str:
    """Map a roadmap state cell to one stable token."""
    plain = _plain_cell(cell).upper()
    if not plain:
        return UNKNOWN_TEXT
    if plain.startswith("DONE"):
        return "DONE"
    if "IN PROGRESS" in plain:
        return "IN PROGRESS"
    if plain.startswith("BLOCKED"):
        return "BLOCKED"
    if plain.startswith("PARTIAL"):
        return "PARTIAL"
    if "NOT STARTED" in plain:
        return "NOT STARTED"
    if plain.startswith("PENDING"):
        return "PENDING"
    return UNKNOWN_TEXT
