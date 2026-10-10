# Codex assets in this kit

- `roles/` contains reusable fallback prompt contracts for common engineering responsibilities. These Markdown files do not register native Codex agents.
- `ticketing/` contains the local ticket state helper, discovery script, templates, orchestration contract, and team-routing guidance.
- `knowledge/` contains generic starter notes; replace them with verified knowledge from the target project.
- The kit intentionally ships no `.codex/config.toml` or project-specific `.codex/agents/` registrations. Discover and reuse each target project's own agents; never overwrite its configuration.
