---
name: process-ticket
description: Orchestrate an engineering ticket in its own Git worktree through implementation, review, QA, commit and pull request; stop for human testing and never merge.
---
# Process Ticket — Lead Orchestrator

Read repository `AGENTS.md`, `AGENTS.ticket-addon.md`, ticket file/state, `.codex/knowledge/`, and `.codex/ticketing/orchestration.md`. First follow `$discover-team` (or its instructions) to inventory actual repository skills and registered agents; choose existing specialists first and document role mapping in `plan.md`.

## Isolated workspace and ticket records

- Give each ticket one branch named `codex/<TICKET-ID>` and one dedicated Git worktree. The AgentOps dashboard prepares and reuses this worktree for processing and correction runs. When started elsewhere, use a separate Codex worktree for this ticket before editing. Never edit two tickets in the same working tree. If the current runtime cannot provide an isolated worktree, stop before edits and report the limitation.
- Keep ticket records in their canonical ticket directory. The dashboard supplies that absolute path and grants access to it; use it for all ticket files and attachments. Pass `--ticket-dir "<absolute-ticket-directory>"` to `ticket.py show`, `check`, and `set-status` when it is outside the current worktree. Without an explicit path, the helper searches the current checkout's `tickets/` and `.codex/tickets/` folders.
- Record the branch, worktree path, and starting commit in `plan.md`. Preserve unrelated changes already present in a resumed ticket worktree.
- Run only one processing session for a given ticket at a time. Different tickets can proceed concurrently in their separate worktrees. Keep delegated edits within disjoint files or additional isolated worktrees.

## Required phases

1. INVESTIGATING: map affected code and current architecture; reproduce safely when feasible; record commands, observed outcomes, and uncertainty in `investigation.md`. For features, map current behavior and integration points.
2. PLANNING: create `plan.md` with dependencies, tasks, assigned specialist roles, file boundaries, acceptance criteria, tests, rollback notes, and risks. Identify potentially incompatible edits. Do not pretend project commands are universal.
3. IMPLEMENTING: assign tasks to discovered existing subagents where supported; only use `.codex/roles/` guidance as fallback. Invoke relevant existing skills as instructions when useful. Parallelize only independent tasks with disjoint file scope/worktrees; otherwise sequential. Each assignee writes a factual report to the canonical ticket's `agent-reports/`. Lead integrates and checks the ticket worktree.
4. REVIEW: independent reviewer + security specialist as warranted. Write issues with severity and actionable evidence; reopen tasks to resolve real findings.
5. QA: QA agent checks acceptance criteria, runs relevant automated checks, records exact commands, environment and outcomes in `qa-report.md`. Static reasoning is not a passing test. If tests cannot run, mark BLOCKED/UNVERIFIED; do not mark PASS.
6. If FAIL: create defect tasks, delegate fixes, rerun applicable tests and QA in the same ticket worktree. Limit to 3 repair cycles, then set Blocked with findings; no false pass.
7. If PASS and documentation is complete, review the final diff, commit the ticket changes, push the assigned branch, and create or update a pull request against the project's intended base branch. Record the worktree path, branch, commit SHA, and pull request URL in `ticket.md` and `qa-report.md`. Leave the pull request open for the requester to test. If the repository has no usable remote or the required host CLI/authentication is unavailable, report Blocked; do not claim a PR exists.
8. Only after QA passes and the pushed commit and pull request are recorded, set status to `Ready for Human Verification` with `python .codex/ticketing/ticket.py set-status ID "Ready for Human Verification" --ticket-dir "<absolute-ticket-directory>" --qa-pass`. This transition also checks that the ticket contains branch, worktree, commit SHA, and pull request URL. Summarize changes, test results, PR link, and remaining risks for human testing.

## Acceptance checklist progress

Keep the acceptance checkboxes in `ticket.md` synchronized as work proceeds. Check an individual criterion only when implementation and recorded evidence support it; leave incomplete or unverified criteria unchecked. Checklist progress is separate from QA status: only move to `Ready for Human Verification` after QA passes and the commit and open PR are available for human testing.

**Native subagent availability:** if orchestration tools exist, delegate with clear role, objective, file ownership, constraints and report path. If they do not, use sequential role passes and disclose that no independent agent execution occurred. Do not claim parallelism that did not happen.

Do not merge, deploy, close a PR, or mark human verification complete. A human can test the open PR and then approve or reject the ticket. Approval may move the ticket to `Done`, but the human still decides when to merge. On rejection, update the same branch and PR from the same ticket worktree.

## Agent discovery requirement
Do not hardcode specialist names. Run `python .codex/ticketing/discover.py --root . --out .codex/ticketing/team-inventory.json` at the start of every ticket. Read `.codex/ticketing/agent-routing.md`; add a role mapping and actual delegation method to the ticket plan. Never overwrite an existing `.codex/config.toml`.
