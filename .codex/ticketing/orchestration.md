# Ticket State Machine & Delegation Contract

`Open → Investigating → Planning → Implementing → Code Review → QA Testing (commit, push, PR) → Ready for Human Verification → Done`.

Failure paths: Code Review → Implementing; QA Testing → Implementing; any active stage → Blocked; Blocked → Investigating / Planning / Implementing when evidence supports resumption; Ready for Human Verification → Implementing after human rejection.

Only lead changes status. Code edits only while Implementing or repairs. Each transition must be documented in the ticket and updated by `ticket.py`. `Ready for Human Verification` requires passing QA plus a committed, pushed branch and an open pull request recorded in the ticket. `Done` records human acceptance; it does not mean the pull request was merged.

## Ticket worktrees and delivery

Every processed ticket owns a branch named `codex/<TICKET-ID>` and a dedicated Git worktree. The dashboard creates the worktree beside the selected repository under `<repository-name>-ticket-worktrees/<TICKET-ID>` and reuses it for correction runs. Keep concurrent tickets on distinct branches and worktrees; never launch two runs for the same ticket. Preserve ticket records and attachments in their canonical folder, which may be outside the code worktree. Pass its absolute path with `ticket.py --ticket-dir` for state commands and use it for all ticket reports.

After review and passing QA, commit the ticket changes, push the branch, and create or update a pull request targeting the repository's intended base branch. Record the worktree path, branch, commit SHA, and pull request URL in `ticket.md` and `qa-report.md`. Leave the PR open so the requester can test it. If branch push or PR creation is unavailable, keep the ticket Blocked and record the reason. Never merge or close the PR automatically. On human rejection, resume the same ticket worktree and update the same branch and PR.

Delegation envelope must specify: ticket ID, task ID, agent role, exact objective, affected files (exclusive owner if editing), upstream dependencies, constraints, tests, deliverable path and stop conditions. Never spawn multiple editors on one file simultaneously. Prefer separate worktrees when roles overlap.

Review and QA must not simply trust implementation claims. Review diffs and execute tests. Assign skeptical security review for auth, payments, data integrity, privacy and external integrations.

Quality gate: explicit acceptance-criteria matrix; tests with command, exit code, and results; important negative cases; recorded unknowns. No evidence = BLOCKED, not PASS. Max three autonomous fix/retest cycles. Passing QA alone is insufficient for human verification: the commit and open PR must also be recorded. The human tests the PR and separately decides whether and when to merge.

Plan tasks are the source of truth for dependencies. Limit concurrent assignments to installed Codex capabilities; do not assume all Codex versions expose configurable parallel subagents.
