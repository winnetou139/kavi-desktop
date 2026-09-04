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
