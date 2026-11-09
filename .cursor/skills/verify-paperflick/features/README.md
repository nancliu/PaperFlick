# PaperFlick verification map

Maintained source for verifying user-facing PaperFlick behavior. Read this index, then the matching feature file.

## Baseline preconditions

- Run under mamba env `paperflick` with `pip install -e .`.
- Set `PAPERFLICK_APPDATA` to a disposable directory for the run.
- Prefer in-process `MainWindow` when no interactive display is required.
- Never drive a PaperFlick instance that was not started by this verification run.

## Driving conventions

- Start from defaults (`Settings()`) unless a feature lists other preconditions.
- Persist checks read `settings.json` via `load()` / file contents after the user action.
- Record the feature ID with every artifact.

## Features

- [Boot window and settings](./boot-settings.md) covers launch, defaults, and AppData persistence.
- [Interval and Dry Run controls](./interval-and-dry-run.md) covers symmetric persistence of toggles and interval.
- [Printer sidebar](./printer-sidebar.md) covers installed printer listing and `selected_printer` persistence.
- [Orientation on add](./orientation-on-add.md) covers Auto default, inferred 横向/纵向, and unread fallback.
- [Preview orientation](./preview-orientation.md) covers Landscape, Portrait, and PrinterDefault applied to this item, the same type, or all.
- [List preview and remove](./list-preview.md) covers row-click preview, inline 移除, 移除全部失败, and showing the preview before its thumbnail loads.
- [PDF real print](./pdf-real-print.md) covers SumatraPDF submit with Dry Run off, interval, orientation, and a missing engine.
- [Image real print](./image-real-print.md) covers Pillow and Windows submit with Dry Run off, interval, orientation, and a failed image that does not stop the Batch.
- [DOCX real print](./docx-real-print.md) covers Word, then OnlyOffice, with Dry Run off. An item that both engines reject stays failed and the Batch continues.
- [Batch end report and spooler gate](./batch-end-report.md) covers the finish line `本批完成：成功 N、失败 M` and waiting for an empty printer queue before the next file.
