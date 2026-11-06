# Coding standards (reviewer)

Mechanical rules are enforced by **ruff** and **pytest** (pre-commit / CI). This file is only for **judgement calls** the tools cannot catch.

## Settings and boundaries

- Parse and coerce persisted fields in `paperflick.core.settings` (or another explicit boundary module), not duplicated inside UI widgets.
- UI widgets may format for display; they call the shared coerce/load/save helpers rather than re-implementing validation.

## Persistence symmetry

- Controls that represent the same `Settings` fields should persist with the same urgency. If a checkbox writes on change, a related text field must not silently require an unrelated focus event before the value can survive a crash or kill.
