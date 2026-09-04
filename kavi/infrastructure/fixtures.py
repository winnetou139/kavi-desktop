"""Development fixture data.

Derived from the UI/UX concept at
`KAVI_Vault_v0.1/Kimi_Agent_Kavinya Desktop UI_UX/app/`.

EVERY record here carries ``origin: "FIXTURE"``. Fixture data is design material
for exercising the interface. It is NOT KAVI company evidence, NOT venture
evidence, and NOT commercial validation, and the interface labels it as such
wherever it appears.

The one exception is the VECYRA venture record, which mirrors the Founder-set
canonical baseline in `05_PRODUCTS/VECYRA/VECYRA Current Venture State.md`
(D-006: VALIDATE / G2 / NOT PASSED) so the cockpit does not contradict the vault.
"""

from __future__ import annotations

from typing import Any

FIXTURE = "FIXTURE"


def actors() -> list[dict[str, Any]]:
    return [
        {
            "id": "ACT-2026-001",
            "name": "Founder",
            "kind": "HUMAN",
            "role": "CEO / Approver",
            "may_approve": True,
            "origin": FIXTURE,
            "notes": "Human authority is explicit. Founder-reserved actions stay human-approved.",
        },
        {
            "id": "ACT-2026-002",
            "name": "Chief of Staff",
            "kind": "ROLE",
            "role": "KAVI Office",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Organizational role. Constrains actors; cannot itself hold an executable grant.",
        },
        {
            "id": "ACT-2026-003",
            "name": "INTEL Lead",
            "kind": "ROLE",
            "role": "INTEL",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Division role for research and evidence work.",
        },
        {
            "id": "ACT-2026-004",
            "name": "Ephemeral Research Worker",
            "kind": "AGENT_INSTANCE",
            "role": "INTEL",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Bounded worker. Produces evidence; may not approve its own output.",
        },
        {
            "id": "ACT-2026-005",
            "name": "Independent Reviewer",
            "kind": "AGENT_INSTANCE",
            "role": "CONTROL",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Reviewer identity must differ from the producer identity.",
        },
        {
            "id": "ACT-2026-006",
            "name": "Vault Indexer",
            "kind": "SERVICE_ACCOUNT",
            "role": "OPERATE",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Service account. May execute under a grant; can never issue an approval.",
        },
        {
            "id": "ACT-2026-007",
            "name": "Hermes",
            "kind": "PROVIDER",
            "role": "Agent / Orchestration Runtime",
            "may_approve": False,
            "origin": FIXTURE,
            "notes": "Execution capability, not an authority-bearing actor (D-002).",
        },
    ]


def permissions() -> list[dict[str, Any]]:
    return [
        {
            "id": "GNT-2026-001",
            "actor_id": "ACT-2026-004",
            "action": "RESEARCH_READ",
            "resource": "public web sources",
            "scope": "desk research only, no outreach",
            "conditions": "No external contact. No spending. No customer communication.",
            "budget": "0 external spend",
            "expiry": "on objective completion",
            "approver_id": "ACT-2026-001",
            "state": "ACTIVE",
            "origin": FIXTURE,
        },
        {
            "id": "GNT-2026-002",
            "actor_id": "ACT-2026-005",
            "action": "REVIEW_WRITE",
            "resource": "review records",
            "scope": "objectives it did not produce",
            "conditions": "Reviewer identity must differ from producer identity.",
            "budget": "0 external spend",
            "expiry": "on objective completion",
            "approver_id": "ACT-2026-001",
            "state": "ACTIVE",
            "origin": FIXTURE,
        },
        {
            "id": "GNT-2026-003",
            "actor_id": "ACT-2026-006",
            "action": "VAULT_READ",
            "resource": "KAVI Vault",
            "scope": "read only",
            "conditions": "No writes. No synchronization.",
            "budget": "n/a",
            "expiry": "none",
            "approver_id": "ACT-2026-001",
            "state": "ACTIVE",
            "origin": FIXTURE,
        },
        {
            "id": "GNT-2026-004",
            "actor_id": "ACT-2026-004",
            "action": "EXTERNAL_OUTREACH",
            "resource": "prospective customers",
            "scope": "none",
            "conditions": "Founder approval required before any external contact.",
            "budget": "0",
            "expiry": "—",
            "approver_id": "ACT-2026-001",
            "state": "REVOKED",
            "origin": FIXTURE,
        },
    ]


def ventures() -> list[dict[str, Any]]:
    return [
        {
            "id": "VEN-2026-001",
            "name": "VECYRA",
            "stage": "VALIDATE",
            "gate": "G2 — VALIDATE → OFFER",
            "gate_status": "NOT PASSED",
            "recommendation": "INVESTIGATE",
            "problem": "Contemporaneous delay and disruption evidence capture that survives EOT scrutiny",
            "segment": "MEP / electrical specialty subcontractors, 20–499 employees",
            "commercial_evidence": "UNKNOWN / REQUIRES VALIDATION",
            "hypotheses": [
                "Specialist subcontractors lose EOT/claim entitlement because delay evidence "
                "is not captured contemporaneously.",
                "The budget owner in a 20–499 employee electrical firm is reachable without "
                "enterprise procurement.",
                "Existing tooling does not serve this segment at a price it will pay.",
            ],
            "known_evidence": [
                "Distressed-project disputes average US$56.0m and 12.2 months (Arcadis 16th CDR).",
                "Across 2,204 projects / $2.43tn CapEx, 33.4% of budgets and 65.8% of schedules "
                "were exceeded (HKA CRUX 8th).",
                "'Where there is no contemporary record to support a claim, that claim fails' "
                "(AG Falkland Islands v Gordon Forbes).",
                "7,925 US electrical contracting firms sit in the 20–499 employee band (Census SUSB 2022).",
            ],
            "unknowns": [
                "U1 — Willingness to pay. No signal of any kind.",
                "U2 — Who signs, and at what approval threshold.",
                "U3 — Whether the problem is felt acutely enough to fund.",
                "U4 — Whether the segment is reachable without enterprise procurement.",
                "U5 — Realistic price floor; the observed floor is ~$6k/yr, not $2k.",
                "U6 — Competitor traction in this specific segment.",
                "U7 — SCL and AACE primary texts were never retrieved.",
                "U8 — Whether GCs, not trades, are the real buyer.",
            ],
            "next_validation": (
                "10–15 structured problem interviews with MEP/electrical subcontractors. "
                "No pitching. Founder approval required before any external contact."
            ),
            "blockers": (
                "No buyer-side evidence. No willingness-to-pay signal. "
                "Segment depth thin. Counter-evidence locates the spreadsheet "
                "problem in GCs rather than trades."
            ),
            "next_gate_requirement": (
                "Buyer-side evidence: multiple customer/process data points, "
                "budget owner identified, willingness-to-pay signal or executed test plan."
            ),
            "next_founder_decision": (
                "Approve the recommended problem and segment plus the interview "
                "experiment, or redirect to GCs."
            ),
            "origin": FIXTURE,
        }
    ]


def objectives() -> list[dict[str, Any]]:
    return [
        {
            "id": "OBJ-2026-001",
            "title": "Determine which single VECYRA customer problem and segment deserves advancement toward OFFER",
            "outcome": (
                "One recommended problem, one recommended segment, evidence table "
                "sufficient for a CONTINUE / INVESTIGATE / KILL decision."
            ),
            "state": "COMPLETED",
            "owner_actor_id": "ACT-2026-002",
            "sponsor_actor_id": "ACT-2026-001",
            "permission_grant_id": "GNT-2026-001",
            "priority": "HIGH",
            "authority_level": "A1",
            "constraints": "Desk research only. No outreach. No spend. No product code changes.",
            "success_criteria": (
                "One problem, one segment, an evidence table with every material claim "
                "classified, and a gate recommendation the Founder can act on."
            ),
            "evidence_requirements": "Every material claim classified with source, date, locator, confidence, freshness, contradiction.",
            "budget": "0 external spend",
            "actual_cost": "0 external spend",
            "deadline": "single bounded run",
            "venture_id": "VEN-2026-001",
            "created_at": "2026-09-04T21:00:00",
            "updated_at": "2026-09-04T22:20:00",
            "origin": FIXTURE,
        }
    ]


def tasks() -> list[dict[str, Any]]:
    common = {
        "objective_id": "OBJ-2026-001",
        "owner_actor_id": "ACT-2026-003",
        "assignee_actor_id": "ACT-2026-004",
        "assigned_role_id": "ACT-2026-003",
        "permission_grant_id": "GNT-2026-001",
        "capability_requirements": "REASONING, WEB_READ",
        "authority_level": "A1",
        "priority": "NORMAL",
        "evidence_requirement": "Every material claim classified with source, date, locator, confidence.",
        "review_required": True,
        "approval_required": False,
        "estimated_cost": "0 external spend",
        "actual_cost": "0 external spend",
        "retry_policy": "no retry; single bounded run",
        "created_at": "2026-09-04T21:00:00",
        "updated_at": "2026-09-04T22:20:00",
        "origin": FIXTURE,
    }
    return [
        {
            **common,
            "id": "TASK-2026-001",
            "title": "Market structure and buyer segments",
            "state": "DONE",
            "expected_output": "Evidence table on segmentation, budget ownership, tool usage, reachability",
            "idempotency_key": "obj001-market",
            "started_at": "2026-09-04T22:06:21",
            "completed_at": "2026-09-04T22:14:27",
        },
        {
            **common,
            "id": "TASK-2026-002",
            "title": "Problem cost and frequency evidence",
            "state": "DONE",
            "expected_output": "Ranked evidence on ten candidate project-control problems",
            "idempotency_key": "obj001-problems",
            "started_at": "2026-09-04T22:06:21",
            "completed_at": "2026-09-04T22:11:30",
        },
        {
            **common,
            "id": "TASK-2026-003",
            "title": "Competitive landscape and pricing",
            "state": "DONE",
            "expected_output": "Vendor map, published price anchors, underserved gaps",
            "idempotency_key": "obj001-competitors",
            "started_at": "2026-09-04T22:06:21",
            "completed_at": "2026-09-04T22:10:22",
        },
        {
            **common,
            "id": "TASK-2026-004",
            "title": "Delay and claims economics, evidence burden",
            "state": "DONE",
            "expected_output": "Dispute economics, records standards, exposure by party",
            "idempotency_key": "obj001-claims",
            "started_at": "2026-09-04T22:06:21",
            "completed_at": "2026-09-04T22:11:18",
        },
        {
            **common,
            "id": "TASK-2026-005",
            "title": "Synthesis and CEO decision brief",
            "state": "DONE",
            "assignee_actor_id": "ACT-2026-002",
            "expected_output": "One problem, one segment, evidence table, alternatives, unknowns, next experiment",
            "idempotency_key": "obj001-synthesis",
            "started_at": "2026-09-04T22:15:00",
            "completed_at": "2026-09-04T22:19:00",
        },
        {
            **common,
            "id": "TASK-2026-006",
            "title": "Independent review of brief and evidence register",
            "state": "REVIEW",
            "assignee_actor_id": "ACT-2026-005",
            "permission_grant_id": "GNT-2026-002",
            "expected_output": "PASS / PASS_WITH_CONDITIONS / FAIL with exact findings",
            "idempotency_key": "obj001-review",
            "started_at": "2026-09-04T22:20:00",
            "completed_at": "",
        },
        {
            **common,
            "id": "TASK-2026-007",
            "title": "Customer interviews — MEP subcontractors",
            "state": "BLOCKED",
            "priority": "HIGH",
            "depends_on": "TASK-2026-006",
            "approval_required": True,
            "permission_grant_id": "GNT-2026-004",
            "expected_output": "10–15 structured problem interviews",
            "idempotency_key": "obj001-interviews",
            "failure_reason": "",
            "started_at": "",
            "completed_at": "",
        },
    ]


def evidence() -> list[dict[str, Any]]:
    return [
        {
            "id": "CLM-2026-001",
            "claim": "US average construction dispute value $56.0m, duration 12.2 months",
            "classification": "FACT",
            "source": "Arcadis 16th Global Construction Disputes Report",
            "source_date": "2025",
            "locator": "Arcadis CDR 16th edition",
            "confidence": "HIGH",
            "freshness": "Current",
            "contradiction": "Value fell from $60.1m / 12.5 months in the 15th CDR — severity trend is downward",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-002",
            "claim": "Across 2,204 projects, disputed sums equal 33.4% of contract budgets; EOT claims equal 65.8% of planned schedules",
            "classification": "FACT",
            "source": "HKA CRUX 8th edition",
            "source_date": "2025",
            "locator": "HKA CRUX Insight 8th",
            "confidence": "HIGH",
            "freshness": "Current",
            "contradiction": "Sample covers distressed projects; denominator unpublished, so this is not a population base rate",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-003",
            "claim": "Where there is no contemporary record to support a claim, that claim fails; witness statements cannot substitute",
            "classification": "FACT",
            "source": "AG Falkland Islands v Gordon Forbes",
            "source_date": "2003",
            "locator": "Judgment, Falkland Islands",
            "confidence": "HIGH",
            "freshness": "Old but leading authority",
            "contradiction": "Skitmore regression (n=11) found only programme and drawing records improved recovery",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-004",
            "claim": "Records failure is the mechanism by which claims fail, not a ranked cause of disputes",
            "classification": "INFERENCE",
            "source": "Derived from Arcadis CDR cause ranking and Gordon Forbes",
            "source_date": "2026-09-04",
            "locator": "OBJ-2026-001 Evidence Register CLM-005",
            "confidence": "MEDIUM",
            "freshness": "Current",
            "contradiction": "Changes the sales narrative: the felt pain is lost entitlement, not record-keeping hygiene",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-005",
            "claim": "77% of GCs perform project controls in spreadsheets even when they already own an ERP",
            "classification": "FACT",
            "source": "Dodge / CMiC, n=216 GCs and 123 trades",
            "source_date": "2025-03/04",
            "locator": "Dodge Construction Network study",
            "confidence": "HIGH",
            "freshness": "Current",
            "contradiction": "Same study locates trades' spreadsheet dominance in inventory/equipment — cuts against the MEP wedge",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-006",
            "claim": "Only 7,925 US electrical contractors sit in the 20–499 employee band",
            "classification": "FACT",
            "source": "US Census SUSB, computed from source data",
            "source_date": "2022",
            "locator": "Census SUSB NAICS 238210",
            "confidence": "HIGH",
            "freshness": "4 years old",
            "contradiction": "Reachable-and-viable sub-band is small in absolute terms",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-007",
            "claim": "Willingness-to-pay for VECYRA",
            "classification": "UNKNOWN",
            "source": "",
            "source_date": "",
            "locator": "",
            "confidence": "LOW",
            "freshness": "",
            "contradiction": "Structurally unobservable through desk research. Requires buyer contact.",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
        {
            "id": "CLM-2026-008",
            "claim": "Base rate of claims that fail for want of records",
            "classification": "UNKNOWN",
            "source": "",
            "source_date": "",
            "locator": "",
            "confidence": "LOW",
            "freshness": "",
            "contradiction": "The single most valuable missing number for sizing the problem",
            "objective_id": "OBJ-2026-001",
            "origin": FIXTURE,
        },
    ]


def reviews() -> list[dict[str, Any]]:
    return [
        {
            "id": "REV-2026-001",
            "subject_id": "OBJ-2026-001",
            "reviewer_actor_id": "ACT-2026-005",
            "producer_actor_id": "ACT-2026-004",
            "review_task_id": "TASK-2026-006",
            "review_date": "2026-09-04",
            "independence_conditions": (
                "Reviewer performed no research and no synthesis on this objective and "
                "received no reasoning trace from the synthesis path."
            ),
            "checked_ids": "CLM-2026-001..008, Phase Gates, Opportunity Scoring",
            "findings": "Recorded in the evidence register and CEO brief.",
            "acceptance_criteria": (
                "One problem, one segment, classified claims, no invented commercial "
                "evidence, no gate self-approval, alternatives and unknowns stated."
            ),
            "result": "PENDING",
            "conditions": "",
            "remediation_task_id": "",
            "origin": FIXTURE,
        }
    ]


def approvals() -> list[dict[str, Any]]:
    return [
        {
            "id": "APR-2026-001",
            "subject_id": "TASK-2026-007",
            "approver_actor_id": "ACT-2026-001",
            "state": "PENDING",
            "requester_actor_id": "ACT-2026-002",
            "executor_actor_id": "ACT-2026-004",
            "reviewer_actor_id": "ACT-2026-005",
            "reason": "External customer interviews require explicit Founder approval before any contact.",
            "expiry": "",
            "decided_at": "",
            "origin": FIXTURE,
        },
        {
            "id": "APR-2026-002",
            "subject_id": "VEN-2026-001",
            "approver_actor_id": "ACT-2026-001",
            "state": "PENDING",
            "requester_actor_id": "ACT-2026-002",
            "executor_actor_id": "",
            "reviewer_actor_id": "ACT-2026-005",
            "reason": "Gate advancement toward OFFER. KAVI may not approve its own gate.",
            "expiry": "",
            "decided_at": "",
            "origin": FIXTURE,
        },
    ]


def decisions() -> list[dict[str, Any]]:
    rows = [
        ("D-001", "KAVI is the company; VECYRA is a product",
         "Product portfolio remains open beyond VECYRA."),
        ("D-002", "KAVI must not depend on Hermes",
         "Hermes is an orchestration capability, not canonical company state."),
        ("D-003", "Local desktop is cockpit; VPS is engine room",
         "Future always-on work is separated from Founder-laptop uptime."),
        ("D-004", "Problem and validation precede serious product build",
         "Venture work follows evidence and phase gates."),
        ("D-005", "KAVI Vault is the canonical organizational knowledge source",
         "Vault owns organizational knowledge; Operational Store owns machine-operational state."),
        ("D-006", "VECYRA baseline is VALIDATE at G2, not passed",
         "Commercial evidence must not be inferred from product maturity."),
    ]
    return [
        {
            "id": identifier,
            "title": title,
            "state": "APPROVED",
            "owner_actor_id": "ACT-2026-001",
            "approver_actor_id": "ACT-2026-001",
            "date": "2026-09-04",
            "context": "",
            "decision": title,
            "rationale": consequence,
            "evidence_ids": "",
            "consequences": consequence,
            "reversible": "Yes",
            "supersedes": "",
            "origin": FIXTURE,
        }
        for identifier, title, consequence in rows
    ]


def inbox() -> list[dict[str, Any]]:
    """Fixture inbox items.

    Each references a real underlying object so the aggregation semantics are
    demonstrated correctly. They remain FIXTURE and cannot be decided; create a
    local item from a real object to exercise Founder disposition.
    """
    return [
        {
            "id": "INB-2026-001",
            "type": "DECISION",
            "risk": "MEDIUM",
            "title": "VECYRA problem and segment selection",
            "subject_kind": "OBJECTIVE",
            "subject_id": "OBJ-2026-001",
            "objective_id": "OBJ-2026-001",
            "recommendation": (
                "Recommend contemporaneous delay-evidence capture for MEP/electrical "
                "subcontractors. Gate recommendation: REMAIN IN VALIDATE."
            ),
            "evidence_ids": ["CLM-2026-001", "CLM-2026-002", "CLM-2026-003", "CLM-2026-005", "CLM-2026-006"],
            "authority_note": (
                "Fully reversible. No spend, no outreach, no code. KAVI may not "
                "advance the gate; Founder approval required."
            ),
            "state": "OPEN",
            "disposition_note": "",
            "decided_at": "",
            "created_at": "2026-09-04T22:20:00",
            "origin": FIXTURE,
        },
        {
            "id": "INB-2026-002",
            "type": "APPROVAL",
            "risk": "MEDIUM",
            "title": "Authorize customer interviews (external contact)",
            "subject_kind": "TASK",
            "subject_id": "TASK-2026-007",
            "objective_id": "OBJ-2026-001",
            "recommendation": (
                "Approve 10-15 structured problem interviews per the Validation Protocol. "
                "No pitching. The task is BLOCKED until approved."
            ),
            "evidence_ids": ["CLM-2026-007"],
            "authority_note": "First external contact. Founder-reserved. Approval APR-2026-001 pending.",
            "state": "OPEN",
            "disposition_note": "",
            "decided_at": "",
            "created_at": "2026-09-04T22:21:00",
            "origin": FIXTURE,
        },
        {
            "id": "INB-2026-003",
            "type": "RISK",
            "risk": "HIGH",
            "title": "Counter-evidence contradicts the recommended segment",
            "subject_kind": "VENTURE",
            "subject_id": "VEN-2026-001",
            "objective_id": "OBJ-2026-001",
            "recommendation": (
                "Dodge/CMiC locates the project-controls spreadsheet problem in GCs (77%), "
                "not trades. Consider redirecting the segment before spending interview budget."
            ),
            "evidence_ids": ["CLM-2026-005"],
            "authority_note": "Contradiction preserved, not discarded. Founder judgement required.",
            "state": "OPEN",
            "disposition_note": "",
            "decided_at": "",
            "created_at": "2026-09-04T22:21:30",
            "origin": FIXTURE,
        },
        {
            "id": "INB-2026-004",
            "type": "FYI",
            "risk": "LOW",
            "title": "Foundation Hardening passed independent review",
            "subject_kind": "DECISION",
            "subject_id": "D-005",
            "objective_id": "",
            "recommendation": "Four foundational contracts are canonical at v0.2. Zero blockers.",
            "evidence_ids": [],
            "authority_note": "No action required.",
            "state": "OPEN",
            "disposition_note": "",
            "decided_at": "",
            "created_at": "2026-09-04T21:58:00",
            "origin": FIXTURE,
        },
    ]


def all_fixtures() -> dict[str, list[dict[str, Any]]]:
    return {
        "actors": actors(),
        "permissions": permissions(),
        "objectives": objectives(),
        "tasks": tasks(),
        "evidence": evidence(),
        "reviews": reviews(),
        "approvals": approvals(),
        "decisions": decisions(),
        "ventures": ventures(),
        "inbox": inbox(),
    }
