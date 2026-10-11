# Agentic Ticket Lifecycle

A portable, local-first ticket workflow for Codex. Install it into an existing project without replacing that project's instructions, skills, registered agents, or Codex configuration. It uses your signed-in Codex CLI account; no API key or hosted service is required.

## Included

- Five skills under `.agents/skills/`: `create-ticket`, `discover-team`, `process-ticket`, `project-init`, and `verify-ticket`.
- Specialist role prompts under `.codex/roles/`. These are fallback role contracts, not native registered Codex agents; target-project agents take precedence.
- Ticket lifecycle helpers, discovery, orchestration rules, templates, install playbook, non-destructive installers, and automated tests.
- Copy-ready prompts under `prompts/`.
- Optional standalone dashboard under `agentops-ticket-dashboard/`.

## Project map

- `.agents/skills/` contains the five reusable Codex workflow skills.
- `.codex/ticketing/` contains ticket state and discovery tools, lifecycle rules, routing guidance, and templates.
- `.codex/roles/` contains fallback role prompts. These files do not register native Codex agents.
- `.codex/knowledge/` contains starter notes. Run `$project-init` in the target project to replace them with verified project context.
- `prompts/` contains copy-ready prompts for common workflow steps.
- `agentops-ticket-dashboard/` is an optional local UI for viewing tickets and launching Codex runs.
- `tests/` and `agentops-ticket-dashboard/tests/` contain the kit and dashboard test suites.

## Requirements

- Python 3.9 or newer for the installer and ticket helper scripts.
- Git installed in target projects for ticket-specific worktrees, commits, and branches.
- Codex CLI installed and signed in to create or process tickets. The kit does not need an API key or hosted service.
- The optional dashboard also requires Codex CLI on `PATH`; see its [README](agentops-ticket-dashboard/README.md) for platform-specific setup.

## Install into a project

From this repository, run one of these commands with the target project path:

```powershell
.\install.ps1 -Target "D:\Projects\my-project"
```

```text
python install.py "D:\Projects\my-project"
```

The installer skips existing files and does not replace `.codex/config.toml`. If the target already has `AGENTS.md`, review `AGENTS.ticket-addon.md` and merge its ticket rules deliberately. Read `CODEX_INSTALL.md` for the complete safe installation workflow.

## Use the workflow

1. After installation, run `$project-init` in the target project to record verified architecture, conventions, and test commands in `.codex/knowledge/`. Refresh these notes as the project changes.
2. Before processing a ticket, run `$discover-team` and inspect the generated inventory and routing suggestions. Existing project agents take precedence; bundled role prompts are fallbacks.
3. Run `$create-ticket <description>` to document a request. Ticket creation records the request and does not implement it.
4. Only after explicitly authorizing implementation, run `$process-ticket TKT-0001` in a Codex worktree, or start it from the dashboard, which creates the ticket worktree for you. Each ticket uses its own branch and Git worktree, then is reviewed, QA-tested, committed, pushed, and opened as a pull request. The workflow stops at `Ready for Human Verification` with the PR open for your test and merge decision.
5. Keep acceptance checkboxes in `tickets/TKT-XXXX/ticket.md` current only when each criterion has supporting implementation and evidence. Leave incomplete or unverified criteria unchecked.
6. Test the open PR yourself, then use `$verify-ticket TKT-0001` with an explicit approval or rejection. `Done` records your acceptance; it does not merge the PR or authorize deployment.

The optional dashboard creates and reuses one worktree at `<repository-parent>/<repository-name>-ticket-worktrees/TKT-XXXX` per processed ticket. Different tickets can run at the same time on separate branches and worktrees. Corrections after rejection continue on the same ticket branch and update its existing PR. Worktrees remain available for human testing and are not removed by the dashboard.

Generated ticket records are ignored by default because they can contain private reports or attachments.

## Optional dashboard

Start the dashboard for a target project with:

```powershell
.\agentops-ticket-dashboard\start.ps1 -Repo "D:\Projects\my-project"
```

Connect several repositories to the same dashboard with `-Repo "D:\Projects\one","D:\Projects\two"`, or use the dashboard’s **+** folder button while it is running.

Or run the Python server directly:

```text
python agentops-ticket-dashboard/server.py --repo "D:\Projects\my-project" --repo "D:\Projects\another-project" --port 8765
```

Open <http://127.0.0.1:8765>. Ticket status and acceptance progress come from saved files. The active-ticket count is status-based. See `agentops-ticket-dashboard/README.md`.

## Tests

Run the kit suite from the repository root:

```text
python -m unittest discover -s tests -v
```

Run the dashboard suite from the repository root:

```text
python -m unittest discover -s agentops-ticket-dashboard/tests -v
```
