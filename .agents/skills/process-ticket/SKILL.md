---
name: process-ticket
description: Orchestrate an existing engineering ticket through reproduction, planning, specialist implementation, independent review, testing and QA; finish at human verification, never auto-merge.
---
# Process Ticket — Lead Orchestrator

Read repository `AGENTS.md`, `AGENTS.ticket-addon.md`, ticket file/state, `.codex/knowledge/`, and `.codex/ticketing/orchestration.md`. First follow `$discover-team` (or its instructions) to inventory actual repository skills and registered agents; choose existing specialists first and document role mapping in `plan.md`. Before any edits check git status; do not overwrite unrelated work. Use `python .codex/ticketing/ticket.py show ID` for status.

## Required phases

1. INVESTIGATING: map affected code and current architecture; reproduce safely when feasible; record commands, observed outcomes, and uncertainty in `investigation.md`. For features, map current behavior and integration points.
2. PLANNING: create `plan.md` with dependencies, tasks, assigned specialist roles, file boundaries, acceptance criteria, tests, rollback notes, and risks. Identify potentially incompatible edits. Do not pretend project commands are universal.
3. IMPLEMENTING: assign tasks to discovered existing subagents where supported; only use `.codex/roles/` guidance as fallback. Invoke relevant existing skills as instructions when useful. Parallelize only independent tasks with disjoint file scope/worktrees; otherwise sequential. Each assignee writes a factual report to `agent-reports/`. Lead integrates and checks working tree.
4. REVIEW: independent reviewer + security specialist as warranted. Write issues with severity and actionable evidence; reopen tasks to resolve real findings.
5. QA: QA agent checks acceptance criteria, runs relevant automated checks, records exact commands, environment and outcomes in `qa-report.md`. Static reasoning is not a passing test. If tests cannot run, mark BLOCKED/UNVERIFIED; do not mark PASS.
6. If FAIL: create defect tasks, delegate fixes, rerun applicable tests and QA. Limit to 3 repair cycles, then set Blocked with findings; no false pass.
7. If PASS and documentation complete: set status `Ready for Human Verification` using `ticket.py set-status ID "Ready for Human Verification" --qa-pass` (only after QA report has actual evidence and `Result: PASS`). Summarize changes, tests and remaining risks. Optionally open draft PR with authenticated `gh` only if user requested.

## Acceptance checklist progress

Keep the acceptance checkboxes in `ticket.md` synchronized as work proceeds. Check an individual criterion only when implementation and recorded evidence support it; leave incomplete or unverified criteria unchecked. Checklist progress is separate from QA status: only move to `Ready for Human Verification` after the required QA evidence passes.

**Native subagent availability:** if orchestration tools exist, delegate with clear role, objective, file ownership, constraints and report path. If they do not, use sequential role passes and disclose that no independent agent execution occurred. Do not claim parallelism that did not happen.

Do not merge, deploy, close a ticket, or mark human verification complete. Observe transition rules in `.codex/ticketing/orchestration.md`.

## Agent discovery requirement
Do not hardcode specialist names. Run `python .codex/ticketing/discover.py --root . --out .codex/ticketing/team-inventory.json` at the start of every ticket. Read `.codex/ticketing/agent-routing.md`; add a role mapping and actual delegation method to the ticket plan. Never overwrite an existing `.codex/config.toml`.
