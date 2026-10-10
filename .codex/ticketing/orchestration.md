# Ticket State Machine & Delegation Contract

`Open → Investigating → Planning → Implementing → Code Review → QA Testing → Ready for Human Verification → Done`.

Failure paths: Code Review → Implementing; QA Testing → Implementing; any active stage → Blocked; Blocked → Investigating / Planning / Implementing when evidence supports resumption; Ready for Human Verification → Implementing after human rejection.

Only lead changes status. Code edits only while Implementing or repairs. Each transition must be documented in the ticket and updated by `ticket.py`.

Delegation envelope must specify: ticket ID, task ID, agent role, exact objective, affected files (exclusive owner if editing), upstream dependencies, constraints, tests, deliverable path and stop conditions. Never spawn multiple editors on one file simultaneously. Prefer separate worktrees when roles overlap.

Review and QA must not simply trust implementation claims. Review diffs and execute tests. Assign skeptical security review for auth, payments, data integrity, privacy and external integrations.

Quality gate: explicit acceptance-criteria matrix; tests with command, exit code, and results; important negative cases; recorded unknowns. No evidence = BLOCKED, not PASS. Max three autonomous fix/retest cycles. On passing QA, no auto-merge; human must inspect.

Plan tasks are the source of truth for dependencies. Limit concurrent assignments to installed Codex capabilities; do not assume all Codex versions expose configurable parallel subagents.
