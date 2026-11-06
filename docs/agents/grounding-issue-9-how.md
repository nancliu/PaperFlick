# Grounding: issue #9 fail retain + reprint

Source: parent read of `feat/issue-9-fail-reprint` @ origin/main tip + product plan §5.

## Overview

BatchSession already continues after a failed submit (`result.ok` false → FAILED + failure_reason, then next Waiting). DryRunSubmit always returns ok=True, so failure path is unexercised in Dry Run. List UI shows status but not failure_reason. No select-only-failed / reprint-failed / clear-succeeded commands or toolbar buttons.

## Key Concepts

- Failed Print Items stay; Batch continues (already in session tick loop).
- **只勾选失败项**: selection helper over list checkboxes.
- **重新打印失败项**: select failed + reset those to Waiting + StartBatch.
- **清除已成功**: remove SUCCESS rows; keep failed (and waiting?).
- Dry Run failure injection for agent verify without a printer.

## How It Works today

1. Start → choose DryRunSubmit → tick claims Waiting → submit → SUCCESS always.
2. FAILED branch exists in `session._on_interval_tick` but Dry Run never hits it.
3. Toolbar: add/remove/clear/start/pause/stop only (`main_window.py`).

## Where Things Live

| Concern | Path |
| --- | --- |
| Status + failure_reason | `core/batch/types.py` PrintItem |
| Commands | `core/batch/commands.py` |
| Reduce | `core/batch/reduce.py` |
| Tick + submit | `core/batch/session.py` |
| DryRunSubmit | `core/submit/dry_run.py` |
| List / toolbar | `ui/item_list.py`, `ui/main_window.py` |

## Gotchas

- Reprint must reset FAILED→Waiting then Start; do not invent a second runner. A second Start alone does not re-queue FAILED rows.
- Clear-succeeded vs ClearItems (all) are different.
- Injection should stay at submit boundary (PrintSubmitPort), not scatter ifs in reduce.
- CountsChanged already tracks failed/success. List does not show `failure_reason` yet; #9 should surface it.
- Selection is UI-only (checkboxes), not BatchState. “只勾选失败项” is a list helper, not a domain command unless design argues otherwise.
- `submit_factory` test doubles do not prove Dry Run injection; product path must go through `DryRunSubmit` (or the port `choose_submit_port` returns for dry_run).

## How explainer (90cc7e0d)

Confirmed: failed branch already continues the Batch; DryRunSubmit never fails; no select-failed / reprint / clear-succeeded UI or commands.
