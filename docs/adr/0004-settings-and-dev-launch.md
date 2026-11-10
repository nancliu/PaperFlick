# Settings in AppData; dual launch paths

User preferences (last printer, interval, wait-for-empty-queue, dry-run flag) live in **`%APPDATA%\PaperFlick\settings.json`**, not in the repo.

**Dev / contributor launch** stays **mamba env `paperflick` + `python -m paperflick`** (or the console script).

**Distributed Windows builds** use **Nuitka folder/`dist` mode + Inno Setup** (see `docs/agents/release-checklist.md`). The frozen binary does not embed SumatraPDF, Word, or OnlyOffice; those remain host-machine dependencies discovered at runtime.
