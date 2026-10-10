---
name: project-init
description: Discover and document current project tech stack, architecture, coding conventions, test commands and changed dependencies for use by ticket agents.
---
# Project Initialization / Refresh

Explore repository safely. Read package manifests, configs, documentation, tests, routes and directory structure; do not install dependencies by default. Detect language/framework(s), front/back boundaries, data storage, build/test commands, deployment, security boundaries, and existing conventions. Save verified findings with source file links in `.codex/knowledge/architecture.md`, `conventions.md`, `testing.md`. Put uncertainties in a separate section; do not guess. When refreshing, diff current verified state with prior notes and update changed facts, never replace user-maintained guidance without review. Do not expose env secrets or copy their values into knowledge.
