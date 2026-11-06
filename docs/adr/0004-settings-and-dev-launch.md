# Settings in AppData; ship as mamba source first

User preferences (last printer, interval, wait-for-empty-queue, dry-run flag) live in **`%APPDATA%\PaperFlick\settings.json`**, not in the repo. v1 runs from a **mamba env + source entrypoint**; PyInstaller (or similar) waits until a second machine needs a frozen binary.
