# Use Python 3 + mamba for PaperFlick

PaperFlick is a Windows personal batch-print tool that must glue Word COM, SumatraPDF, and the Print Spooler behind a simple GUI. We chose **Python 3 in a mamba-managed env (never base)** over Rust or Go because COM/pywin32 and GUI delivery speed dominate; Rust’s single-binary upside does not pay for COM/GUI cost on v1, and Go is a weak fit for Word COM + desktop UI.
