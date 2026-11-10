# Preview Paper

Prove issue #48. The preview shows a gray canvas and a white Preview Paper sheet whose aspect follows Facing. Landscape and Portrait swap a fixed A4 ratio. PrinterDefault uses an unforced square sheet and the copy 「不强制朝向」. The thumbnail fits inside the sheet. Radio changes update the sheet and draft summary immediately. Apply still writes only Orientation.

## Setup

Disposable `PAPERFLICK_APPDATA`. Construct `MainWindow` headless (or launch the app). No installed printer is required.

## Drive

1. Create a tall PNG (`height > width`) and a wide PNG.
2. `AddPaths` those two files. Both rows are `Orientation.AUTO`.
3. Click the tall PNG row. With the empty Auto radio, the paper height is greater than its width and the draft line shows `纵向`.
4. Choose 横向. The paper width becomes greater than its height and the draft line shows `横向`.
5. Choose 打印机. The paper is square (unforced), and the draft line contains `不强制朝向`.
6. Choose 横向 again. 应用到此项.
7. Click the tall PNG row again. The radio is Landscape, and the paper is landscape aspect.
8. Click the wide PNG row. Empty Auto radio yields landscape paper from shape. Choose 纵向, then 应用到此项. Reopen: Portrait radio and portrait paper.

## Expect

- Auto open with an empty radio matches `resolve_facing(AUTO, shape)` for the sheet.
- Landscape and Portrait immediately swap A4 aspect; content stays fit-inside when a thumbnail exists.
- PrinterDefault never fakes Landscape or Portrait.
- Apply writes Orientation only; reopening matches the stored policy.
- Dry Run / Live submit ports are unchanged by this feature.

## Evidence

`artifacts/preview-paper/log.txt` from `_run_preview_paper.py`. Note headless versus a live window.
