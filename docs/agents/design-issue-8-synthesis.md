# Issue 8 synthesis

Grounding is from the worktree on `feat/issue-8-image-print`, which already contains the SumatraPDF port from issue 6. Arena runners were not spawned. This delegate cannot spawn subagents, so the two shapes below were compared here.

## How

### Overview

A Batch walks Print Items one at a time. `BatchSession` is the only writer. It calls `PrintSubmitPort.submit` once per item and stores `SubmitOk` as success or `SubmitFailed.reason` as `failure_reason`. Dry Run and real print share that loop. ADR 0002 says the no-op happens only at the submit boundary, and that images go out through Pillow and Windows printing.

After issue 6, `choose_submit_port` returns `DryRunSubmit` or `PdfSumatraSubmit`. A non-PDF row fails with `该格式暂不支持打印`. The session does not catch exceptions from `submit`, so a port that raises stops the Batch.

### Key concepts

- **Print Item.** One row. Kind, orientation policy, page shape, status, optional failure reason.
- **PrintSubmitPort.** `submit(SubmitRequest) -> SubmitOk | SubmitFailed`. The session knows this and nothing about Sumatra or the spooler.
- **Facing.** `resolve_facing` returns landscape, portrait, or None. None means leave the printer's current direction alone.

### How it works

Start binds one port for the Batch. The first waiting item is submitted immediately. Later items wait for the interval. A failed submit marks that row and still schedules the next tick.

`PdfSumatraSubmit` preflights, rejects a non-PDF, and runs one Sumatra process. `DryRunSubmit` preflights and never starts a process.

### Where things live

- `src/paperflick/core/submit/port.py` owns the request, the two results, and the unsupported reason.
- `src/paperflick/core/submit/select.py` owns `choose_submit_port`.
- `src/paperflick/core/submit/pdf_sumatra.py` owns the PDF command.
- `src/paperflick/core/batch/session.py` owns the interval loop.

### Gotchas

- A raised exception inside `submit` leaves the row in `printing` and stops the loop. Image failures have to come back as `SubmitFailed`.
- `wait_for_empty_queue` is still stored and does nothing.
- DOCX is issue 7. This change must not print it.
- Page shape ignores EXIF. The printed pixels should match that stored size.

## Candidates

### A. Kind table behind the existing port

`LiveSubmit` holds a dict from `DocKind` to a port. PDF maps to the existing Sumatra port. Image maps to a new `ImageWinSubmit`. Any other kind, including DOCX, returns `该格式暂不支持打印` after preflight. `choose_submit_port` returns `DryRunSubmit` or that one live port. The session stays unchanged.

`ImageWinSubmit` opens the file with Pillow, converts the first frame to RGB on white, and asks a `PageDevice` to draw a fitted rectangle. The Windows device builds a new DEVMODE for portrait or landscape, creates a device context the way the installed pywin32 `print_desktop` demo does, and does not call `SetPrinter`. PrinterDefault passes the current DEVMODE through unchanged.

### B. Image branch inside the PDF port

`PdfSumatraSubmit.submit` grows an image branch and calls pywin32 itself. `choose_submit_port` still returns that one class.

## Screen

A hides the spooler, the DEVMODE, and the fit behind one `submit` call. The public surface stays `PrintSubmitPort`. Adding DOCX later is one new dict entry in a later change, and this change does not add that entry. B puts a second engine inside the Sumatra module. The next reader of that file has to learn both command lines. That is the if-chain model-the-domain tells us not to grow.

A's device protocol is the same idea as the Sumatra `run` injection. Tests record the page instead of starting a document.

## Synthesis decision

Ship A.

A wide image fits inside the printable area, centered, with its aspect kept. A transparent pixel is composited on white. GIF and TIFF print the first frame. EXIF orientation is not applied. No printer name uses the Windows default. A missing printer or a file Pillow cannot open fails that item. A draw error aborts the document so a blank page is not committed, then records `图片打印失败`.

## Operator defaults

- DOCX stays unsupported in this change.
- The saved printer default is not modified. Orientation is per job.
- Verify injects a page device and does not call StartDoc on a real printer.
- A landscape device context on the machine used for this change swapped 4760 by 6814 to 6814 by 4760, and the saved orientation stayed 1. That check is `test_landscape_page_swaps_axes_and_keeps_the_saved_default`.
