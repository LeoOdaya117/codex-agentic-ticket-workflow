---
name: discover-team
description: Discover and reuse repository-specific Codex agents and skills before orchestrating a ticket; produce an inventory and suggest role mappings without overwriting configuration.
---
# Discover Existing Team

1. Run `python .codex/ticketing/discover.py --root . --out .codex/ticketing/team-inventory.json` (or `python3`).
2. Read inventory candidates, `.codex/config.toml`, project `AGENTS.md`, and each relevant agent/skill contract.
3. Build a ticket-specific role assignment table: role → existing agent/skill → rationale → execution method → fallback. Existing repository specialists take precedence over bundled `.codex/roles/*.md` guidance.
4. A skill is an instruction set, **not** a callable subagent. Only assign an actual agent if the active Codex runtime exposes it; otherwise use its instructions as a sequential role pass. Never claim that discovery alone registers an agent.
5. If candidates conflict, select the closest documented specialist and record the reason. Do not edit or replace existing registrations.
6. Re-run discovery before processing each ticket, so newly added agents/skills are recognized. Do not treat the inventory file as authority over current files.
