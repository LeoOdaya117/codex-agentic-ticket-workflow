# AgentOps — Local Codex Ticket Dashboard

A **standalone, dependency-free local monitoring and launch UI** for the existing Codex-focused agentic ticket workflow kit. Built with Python's standard library and a responsive vanilla HTML/CSS/JS frontend. No API key is needed: `codex exec` uses the CLI's existing sign-in.

## What it does

- Reads tickets from `<repo>/tickets/<ID>/` and `<repo>/.codex/tickets/<ID>/`.
- Displays ticket status, acceptance-criteria checkbox counts, investigation, plans, QA reports, and agent report Markdown.
- Counts tickets in Investigating, Planning, Implementing, Code Review, or QA Testing as active, including workflows started outside the dashboard.
- Creates tickets by invoking the existing `$create-ticket` skill via Codex.
- Processes tickets by invoking the existing `$process-ticket` skill via Codex.
- Records human verification approval or rejection. Rejections save feedback and optional evidence, reopen the ticket, and start a correction run.
- Tracks active Codex runs internally to prevent launching a duplicate process for the same ticket. Does not automatically merge, deploy, or approve anything.
- Connects multiple repository folders in one dashboard, with a folder switcher and a local folder picker.

## Requirements

- Windows, macOS, or Linux; Python **3.9+** (3.9 is sufficient for this dashboard).
- Codex CLI on PATH and already authenticated (`codex login status`).
- Your existing repository with installed `$create-ticket` and `$process-ticket` skills. This UI **does not replace or modify those skills**.
- Run on your own machine; the HTTP server binds to `127.0.0.1`, not your LAN.

## Start on Windows (PowerShell)

```powershell
cd D:\Tools\codex-ticket-dashboard
python server.py --repo "D:\Projects\fieldOps" --repo "D:\Projects\roadTrip" --port 8765
```

Visit **http://127.0.0.1:8765**.

Alternatively run `start.ps1 -Repo "D:\Projects\fieldOps","D:\Projects\roadTrip"`.
Use the **+** beside Connected folders to browse for and connect another folder while the dashboard is running. The server is local-only; folder additions made with the picker last until the server stops. To reconnect those folders at the next start, pass each one with another `--repo` (or `-Repo`) argument.

### Use with any repository

From the target repository root, launch the dashboard with the path where this
folder is installed:

```powershell
& "D:\Path\To\agentic-ticket-lifecycle\agentops-ticket-dashboard\start.ps1"
```

The launcher uses the current directory as the target repository and defaults
to port `8765`. To launch from another directory, pass `-Repo "D:\Path\To\project"`;
to connect several, pass `-Repo "D:\Path\To\project","D:\Path\To\another-project"`;
to choose another port, pass `-Port 8766`. Then open <http://127.0.0.1:8765>.

## Start on macOS / Linux

```bash
python3 server.py --repo ~/projects/my-repo --port 8765
```

## How it works

```
Browser localhost:8765
    | HTTP fetch every 2 seconds
Local Python server
    |-- reads tickets/, .codex/tickets/, Markdown/JSON
    |-- launches codex exec --json --sandbox workspace-write
    `-- streams JSON lines into in-memory run history
Existing Codex skills + registered specialist agents
```

**Ticket files remain the source of truth.** “Active tickets” is inferred from the ticket status saved in `state.json`; it indicates workflow phase, not a confirmed live process. Acceptance criteria progress counts checked boxes in `ticket.md` and only changes when the ticket workflow records those checks. The dashboard does not display live Codex run events. Run history and process tracking are held in memory and reset when the dashboard stops.

## Important operational notes

1. Start only **one processing run per ticket**. The dashboard currently does not enforce this at the OS/file level; parallel runs on the same ticket can conflict.
2. A successful Codex process exit is **not** proof that your QA tests passed. Inspect `qa-report.md`, check results, and perform human verification.
3. Run sessions and event history are **in memory**; they reset when this dashboard stops. Ticket files persist.
4. Ticket creation accepts **dragged or browsed file uploads** (up to 10 files and 20 MB total), which are staged inside the selected workspace for the Codex run and removed when it exits. The `$create-ticket` skill copies permitted evidence into the ticket's `attachments/` directory. Local paths remain available as an alternative. Human rejection can upload up to 10 image or file attachments (20 MB total); these are saved under the ticket's `attachments/` directory and referenced from `verification.md`.
5. The dashboard does not expose authorization controls; **do not expose its port publicly**. Treat anyone with local access to the dashboard as able to trigger Codex operations in the selected repo.
6. Codex sandbox and approval behavior depend on your local installation and configuration. The dashboard selects `workspace-write` mode, and intentionally does not use dangerous full-access flags.
7. On some Windows systems, `codex` is installed as `codex.cmd`, which is used automatically if present on PATH. If launching fails, try invoking the CLI directly and ensure your PATH is correct.

## Compatibility

This interface reads the common ticket documents used in the earlier Codex workflow. It deliberately does not change existing `AGENTS.md`, `.codex/config.toml`, roles, skills, or agent definitions. It also does not require React or Node to run. To add Claude support later, implement an execution adapter in `server.py`, while retaining the same ticket/file schema.

## Test

```bash
python -m unittest discover -s tests -v
```

## Give this to Codex

> Read this README, then integrate AgentOps into my existing repository without overwriting my skills, agents, config, or AGENTS.md. Keep the dashboard as a standalone tool, confirm my ticket paths and installed skill names, run its tests, and show me how to launch it. Do not modify application code or start a ticket until I ask.
