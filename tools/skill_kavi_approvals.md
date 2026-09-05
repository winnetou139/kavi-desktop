---
name: kavi-approvals
description: Use when the Founder asks to see, approve, reject, defer, or request evidence on KAVI inbox items from Telegram. Records the decision in the cockpit and never confirms a write that did not happen.
---

# KAVI approvals

The Founder decides from his phone. You carry out the decision against the
cockpit and report exactly what happened.

## Showing what is waiting

When he asks what needs deciding ("apa yang perlu saya putuskan", "inbox",
"approval", "keputusan"), run:

```bash
cd ~/kavi-status && KAVI_URL=http://127.0.0.1:18760 python3 approvals.py list
```

Present each OPEN item as a short numbered list: id, type, title. Do not
summarise away the id — he needs it to decide.

If the command reports the cockpit is unreachable, say exactly that: the
cockpit on his laptop is not running or the tunnel is down. Do not pretend
there is nothing to decide.

## Recording a decision

When he says to approve / reject / defer / ask for evidence on an item:

```bash
cd ~/kavi-status && KAVI_URL=http://127.0.0.1:18760 python3 approvals.py decide <ID> <APPROVED|REJECTED|DEFERRED|EVIDENCE_REQUESTED>
```

Rules that matter more than convenience:

- Report the script's own output. If it says the decision was not saved,
  tell him it was not saved. Never answer "sudah disetujui" for a write that
  failed — a false confirmation on an approval system is worse than an error.
- An item that is already APPROVED or REJECTED cannot be changed. The domain
  refuses it. Relay that refusal instead of retrying.
- If he is ambiguous about which item, ask. Deciding the wrong item is not
  recoverable.
- Only the Founder decides. You never choose a disposition for him, and you
  never infer one from context.

## Language

Reply in Bahasa Indonesia. Keep the state words in English and unchanged:
APPROVED, REJECTED, DEFERRED, EVIDENCE_REQUESTED, OPEN.
