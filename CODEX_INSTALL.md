# Instructions for Codex: install this ticket orchestration kit

You are Codex running in the **target existing repository**. The user has supplied `codex-agentic-ticket-kit-installable.zip` or its extracted folder and wants you to install and integrate this kit safely.

## Your installation task

1. Determine the target repository from the user's workspace. If this is ambiguous, inspect the current working directory and ask only when no repository can be identified.
2. Read this file, `README.md`, `AGENTS.ticket-addon.md`, and `install.py` **before running anything**.
3. Inspect the target repository's `AGENTS.md`, `.agents/skills/`, `.codex/agents/`, `.codex/config.toml`, and existing ticket folders. Check `git status` and preserve all existing work.
4. Run the included non-destructive installer, **without `--force`**:
   - Windows: `powershell -ExecutionPolicy Bypass -File <extracted-kit>/install.ps1 -Target <repository-path>`
   - Cross-platform: `python <extracted-kit>/install.py <repository-path>`
   Python 3.9+ is needed for the helper scripts. Do not install dependencies or change system configuration without permission.
5. When target `AGENTS.md` existed, review the new `AGENTS.ticket-addon.md` and **integrate the ticket-workflow rules into the existing `AGENTS.md` conservatively**. Preserve current instructions and avoid duplicates or conflicting rules. If instructions conflict, report the conflict rather than silently replacing existing rules.
6. **Do not overwrite or auto-edit `.codex/config.toml` or existing agent definitions.** Discover existing registered agents and skills using `python .codex/ticketing/discover.py --root . --out .codex/ticketing/team-inventory.json` from the repository root; review the results and explain whether native subagent registrations already exist.
7. Confirm installed skill files appear under `.agents/skills/` and are accessible to Codex. If this Codex build uses a different supported skill discovery location, adapt after checking its documentation; preserve existing skills.
8. Run the included Python tests (from the *extracted kit*): `python -m unittest discover -s tests -v`. If tests cannot run, report that fact honestly.
9. Summarize added files, skipped conflicts, existing agents reused, any manual configuration still required, and exact commands to begin. Do not create/execute real tickets until requested.

## Operating rules after install

- `$project-init`: build verified project knowledge.
- `$discover-team`: inventory and map available specialists and skills.
- `$create-ticket <description>`: create a formatted ticket from natural language, screenshot or log paths, and repository context. Do not implement.
- `$process-ticket TKT-0001`: lead orchestrator investigates, plans, assigns existing agents, implements, reviews, QA-tests, and stops for human verification. Native parallel agents only when supported by current Codex and safe for independent files/worktrees.
- `$verify-ticket TKT-0001`: record human acceptance/rejection.

The kit uses the signed-in local Codex CLI; **do not request an OpenAI API key**. Do not claim always-on GitHub monitoring, automatic parallelism, or successful QA without real execution evidence. Never merge, deploy, or close tickets automatically.
