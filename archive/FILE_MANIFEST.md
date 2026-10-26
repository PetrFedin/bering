# Source fidelity and preservation ledger (26 October 2026)

## Transfer status

**GitHub:** searchable research documents V7–V14, workbook text-extractions (including recovered V13 first 53 sheets from V14), raw source CSV registers, governance files and methods.

**Separate downloadable original-binary archive:** **31** verified files V8–V14, including seven original Excel workbooks (15, 15, 18, 16, 32, 53 and 72 tabs), Word articles, CSV datasets, V10 network PNG, V14 delivery ZIP, and two builder scripts. SHA-256 checksums are in [SHA256SUMS](../provenance/SHA256SUMS_available_originals.txt) and in archive JSON accompanying the ZIP.

**Not present as original bytes in GitHub:** these 31 files — until a compatible GitHub binary upload mechanism copies them and verifies their SHA-256. The original V7 100-sheet XLSX and related DOCX were found in the personal Library but inaccessible for binary-byte materialization; only their extracted contents are archived in GitHub.

**Older V1–V6:** retained as historic tabs within the V7 master extracted workbook, but stand-alone original files not yet located. No false claims of source restoration.

### Preservation rules

1. Every uploaded source must retain its original filename and checksum.
2. Source PDF/Word/Excel originals are never silently edited; revisions get a new version.
3. A GitHub extraction can be searched but is **not** a working spreadsheet and does not guarantee formula preservation.
4. No private waybills, confidential RFQ answers, secrets or personal details may be added to this repo without redaction and redistribution rights.
5. Avoid Git history rewriting or force pushes.

### Original workbook audit

| Version | Excel sheets | Formula cells | Nonempty cached values | Uncached formula results |
|---|---:|---:|---:|---:|
| V8 | 15 | 1051 | 1051 | 0 |
| V9 | 15 | 190 | 190 | 0 |
| V10 | 18 | 136 | 136 | 0 |
| V11 | 16 | 74 | 74 | 0 |
| V12 | 32 | 219 | 207 | 12 |
| V13 | 53 | 445 | 422 | 23 |
| V14 | 72 | 490 | 455 | **35** |

Audited by loading the original XLSX in openpyxl with `data_only=False` and `data_only=True`; **not a new formula calculation**. No stored formula-error cells were found in these original files, but blank caches must be re-evaluated before claiming live recalculation.

### Missing source list

- Original V7 XLSX and DOCX: Library items; **NOT_COMMITTED_BINARY**.
- Standalone V1–V6 original binaries: **NOT_VERIFIED**.
- Native unpublished carrier offers, waybills, invoices, payments and executed new cargo contracts: **NOT_RECEIVED**.
- Source of exact usable available Oct 2026 Magadan port capacity: published XLS was identified but its contents were **NOT_VERIFIED**.
