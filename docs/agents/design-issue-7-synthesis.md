# Issue #7 synthesis

Grounding is the worktree on `feat/issue-7-docx-print`, after PDF Sumatra landed. Arena runners were not spawned. This delegate cannot spawn subagents, so the two shapes below were compared here.

## How

A Batch walks Print Items one at a time. `BatchSession` calls `PrintSubmitPort.submit` once per item. `SubmitOk` becomes success. `SubmitFailed.reason` becomes the row reason. The Batch schedules the next item either way. Dry Run and real print share that loop. ADR 0002 puts the engine choice at this boundary.

`choose_submit_port` returns `DryRunSubmit` when Dry Run is on. Otherwise it returned only `PdfSumatraSubmit`, which fails a DOCX with `该格式暂不支持打印`. Facing is already resolved by `resolve_facing`. The list has no log pane. `logging` is how an engine name is recorded, same as an unread page in `probe`.

OnlyOffice Desktop Editors publishes no silent-print flag. The command-line flags page lists view, edit, review, and new-file flags. The headless tool that ships in `DesktopEditors\converter\x2t.exe` converts a document to PDF. Format `513` is `AVS_OFFICESTUDIO_FILE_CROSSPLATFORM_PDF`.

## Candidates

### A. One DOCX port beside Sumatra

`DocxJob` is the print command (document, printer or default, facing or none). `DocxSubmit` walks an ordered list of engines, Word then OnlyOffice. `LiveSubmit` maps `DocKind.PDF` to the existing Sumatra port and `DocKind.DOCX` to `DocxSubmit`. Any other kind fails the item. Word is a `DispatchEx` process that always quits. OnlyOffice converts with x2t and spools the PDF through `PdfSumatraSubmit`.

### B. A format registry with a handler per kind

A registry maps every `DocKind` to a handler. Image gets a stub that returns unsupported. Session still sees one port.

## Screen

A hides Word COM, the converter XML, and the PDF handoff behind `submit`. Callers do not learn engine order. B adds a registry and a stub handler for images, which this PR must not print. The next agent can copy the stub. That is two ways to say "not yet".

## Synthesis decision

Ship A. The engine order is the tuple `DOCX_ENGINE_ORDER`, not two booleans. `PAPERFLICK_ONLYOFFICE`, when set, is the only x2t candidate. A missing override does not fall through.

`DispatchEx` keeps Quit off the user's open Word. `FilePrintSetup` uses `DoNotSetAsSysDefault=1`. PrinterDefault does not change Word page setup and omits Sumatra's portrait and landscape tokens on the converted PDF. Images stay `该格式暂不支持打印`.
