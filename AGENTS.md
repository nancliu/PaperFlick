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
- **Build**: pstack `/poteto-mode` owns execution (Feature / Bug fix / …). Parallel runs need isolation (worktree / cloud / disjoint tickets); do not dual-drive one working tree.
- **Verify (runtime)**: `.cursor/skills/verify-paperflick/` once the app can launch. Prefer that skill over one-off `_verify_*.py` scripts.
- **Code review (Matt `/code-review`)**: After each feature PR is pushed (or after a fix round on that PR), before babysit declares merge-ready and before Shipping. Fixed point is the PR base (`main` or parent branch). Spec axis uses the linked GitHub issue; Standards axis uses `CODING_STANDARDS.md` + smell baseline. Spec/Standards findings that block acceptance get a `/poteto-mode` fix round, then re-review that PR. Not a substitute for runtime verify or independent Shipping verifiers. Mechanical style stays on ruff/pytest; judgement stays in `CODING_STANDARDS.md`.
- **Babysit / Shipping**: pstack babysit to merge-ready; Shipping only on explicit land/ship request (or a session grant that says PASS may land). Independent per-PR PASS/PASS+NOTES before merge.
- **Environment retro (Matt `/retro`)**: After each development wave lands (one issue or a parallel wave), before starting the next frontier. Target is the agent environment (AGENTS pointers, CODING_STANDARDS judgement rules, guardrails, verify skill), not product feature code. Land env fixes as their own small PR when they earn it; do not block the next ticket on a pure write-up unless a guardrail is broken.

### Windows shell

Run Python checks as script files: `mamba run -n paperflick python path\\to\\script.py` or `pytest`. Do not pass multi-line programs via `python -c` under PowerShell (the shell splits lines into CMD commands).

### Commit / PR handoff

Before reporting an implementer done or opening a PR: working tree clean of junk, and `git push` so `origin/<branch>` includes every local commit (`git log origin/<branch>..HEAD` empty).

If local commit signing hangs (common with 1Password `op-ssh-sign` timeouts), fall back to HTTPS `origin` and `git -c commit.gpgsign=false commit` for the feature branch; do not block the wave waiting on the signer. The same flag applies to every `git rebase --continue` step (or commit the staged rebase result with `gpgsign=false` first). Keep arena scratch and design bakeoff trees out of the feature PR; leave only `docs/agents/design-issue-*-synthesis.md` (and grounding) when they earn review context.

After a parallel sibling merges, rebase before land: merge conflict in `.cursor/skills/verify-paperflick/SKILL.md` / `features/README.md` means keep **both** feature names in the description and index, not one side. When two real-print PRs both extend `LiveSubmit` / `choose_submit_port`, keep every `DocKind` port and update cross-format batch tests; inject engine stubs so unit tests never launch Word/OnlyOffice/the Windows spooler.

### Missing plugins

If `/deslop` (cursor-team-kit) is unavailable, skip searching for it. Tighten prose by hand and run `/no-comments` when needed.
