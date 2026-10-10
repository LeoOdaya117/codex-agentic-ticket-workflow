---
name: verify-ticket
description: Record a human verifier's approval or rejection of a processed ticket, update status, and route rejected work back to implementation.
---
# Verify Ticket

Read ticket, QA evidence, and human's actual feedback. Never impersonate a human verifier or infer approval from silence.
- Explicit approval: write human verification evidence to `verification.md`, then `python .codex/ticketing/ticket.py set-status ID Done --human-approved`.
- Explicit rejection: document observed deviations and reproduction, set `Implementing`, then recommend `$process-ticket ID`.
- If pending or ambiguous: leave Ready for Human Verification unchanged; ask for explicit decision.
Never merge or deploy merely because status is Done.
