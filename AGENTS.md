## Agent skills

### Issue tracker

Issues live in GitHub Issues for `nancliu/PaperFlick` (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `GLOSSARY.md` + `docs/adr/`. See `docs/agents/domain.md`.
Feature worktrees must include these files (branch from a tip that already has them, or copy from the main checkout before coding).

### Workflow (Matt + pstack)

- **Align**: Matt (`/grill-me`, `/grill-with-docs`, `/wayfinder`, `/to-spec`, `/to-tickets`). Do not start `/implement` in parallel with pstack orchestration.
- **Build**: pstack `/poteto-mode` owns execution. Parallel runs need isolation (worktree / cloud / disjoint tickets); do not dual-drive one working tree.
- **Verify (runtime)**: `.cursor/skills/verify-paperflick/` once the app can launch. Prefer that skill over one-off `_verify_*.py` scripts.
- **Review / tests**: Matt `/tdd` and `/code-review` as needed inside build; not a substitute for runtime verification. Mechanical style is enforced by ruff/pytest (see pre-commit / CI). Judgement calls live in `CODING_STANDARDS.md`.
- **Environment retro**: Matt `/retro` after builds (agent environment, not product code).

### Windows shell

Run Python checks as script files: `mamba run -n paperflick python path\\to\\script.py` or `pytest`. Do not pass multi-line programs via `python -c` under PowerShell (the shell splits lines into CMD commands).

### Commit / PR handoff

Before reporting an implementer done or opening a PR: working tree clean of junk, and `git push` so `origin/<branch>` includes every local commit (`git log origin/<branch>..HEAD` empty).

### Missing plugins

If `/deslop` (cursor-team-kit) is unavailable, skip searching for it. Tighten prose by hand and run `/no-comments` when needed.
