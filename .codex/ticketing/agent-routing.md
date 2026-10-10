# Discovery-first delegation policy

At the beginning of each ticket, run `$discover-team` / `discover.py` and inspect the current inventory. Priority order:
1. Registered native agent that matches task responsibility and file boundaries.
2. Existing project agent instructions + native delegation if supported.
3. Relevant existing project skill applied by a capable agent.
4. Bundled specialist guidance in `.codex/roles/` as a fallback.
5. A clearly reported sequential lead-agent role pass if no native delegation tools exist.

A role label does not imply an independently executing agent. Agent TOML files found on disk must be registered by the active Codex runtime to be callable. Never alter the original `.codex/config.toml` automatically. Read policies for every selected agent; project-specific constraints win over generic fallback guidance unless unsafe.

For every delegation record: role, selected agent, contract path, task ID, file ownership, input context, expected evidence, test command, output report path, and whether it actually ran independently. Allow parallelism only with nonoverlapping edits (or isolated worktrees) and native subagent support. The lead integrates the results and launches an independent review/QA when possible. Unverified QA => Blocked, not Passed.
