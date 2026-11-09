# Preview orientation

Prove issue #5. From the preview, set Landscape, Portrait, or PrinterDefault and apply to this item, the same type, or all. All asks before it writes. List marks update. A Dry Run of that list needs no printer. A file added afterward stays Auto.

## Setup

Disposable `PAPERFLICK_APPDATA`. Construct `MainWindow` headless (or launch the app). No installed printer is required.

## Drive

1. Create a tall PNG (`height > width`), a wide PNG, and a tall one-page PDF.
2. `AddPaths` those three files. Every new row is `Orientation.AUTO`. Tall PNG label is `纵向`. Wide PNG label is `横向`.
3. Click the tall PNG row (the name, not 移除). Choose 横向. 应用到此项.
4. Click the wide PNG row. Choose 打印机. 应用到同类型.
5. Click the PDF row. Choose 纵向. 应用到全部 and cancel the confirm.
6. 应用到全部 again and accept the confirm.
7. Add one more wide PNG.
8. Enable Dry Run, set a short interval, and 开始. Wait until the batch is idle.

## Expect

- After step 3, only the tall PNG is Landscape and its row text contains `横向`. The wide PNG and the PDF stay Auto.
- After step 4, both PNGs are PrinterDefault and their marks are `打印机`. The PDF stays Auto.
- Cancel leaves every orientation unchanged.
- Accept sets every current row to Portrait. The wide PNG mark becomes `纵向`.
- The file added in step 7 is Auto. Earlier rows stay Portrait.
- Dry Run finishes with no printer. Orientations are unchanged while statuses become success.
- Clicking a second row closes the preview that is already open, then opens the new one.
- Opening a preview with no radio chosen does not change the list.
- The preview window shows its summary, orientation choices, and actions before the
  thumbnail is decoded. Image and PDF previews then draw a first-page thumbnail;
  DOCX draws a Windows Shell first-page thumbnail when a preview handler exists.
  A failed decode keeps the text fallback. The window is lifted and focused.

## Evidence

`artifacts/preview-orientation/log.txt` from `_run_preview_orientation.py`. Note headless versus a live window.
