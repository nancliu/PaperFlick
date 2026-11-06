# Print via SumatraPDF, Word→OnlyOffice, and pywin32

Outbound printing is format-specific: **PDF** through detected local **SumatraPDF** silent print; **DOCX** through **Word COM first, OnlyOffice fallback**, with the engine named in logs; **images** and printer/queue control through **pywin32**. We rejected embedding a full PDF engine or a single cross-format print API so v1 stays thin and matches machines that already have Word/Sumatra/OnlyOffice. **Dry Run** shares the batch scheduler and only no-ops at the Print Job submit boundary.
