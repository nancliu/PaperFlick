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
