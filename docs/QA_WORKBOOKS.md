# Workbook audit from original V8–V14 source files

**Method**: read-only openpyxl scan for number of worksheets, formula cells, and availability of cached evaluated values. This is a **structural validation**, not evidence that formulas are mathematically correct or a fresh recalc.

| Version | Sheets | Formula cells | Cached non-null | Missing caches |
|---|---:|---:|---:|---:|
| V08 | 15 | 1,051 | 1,051 | 0 |
| V09 | 15 | 190 | 190 | 0 |
| V10 | 18 | 136 | 136 | 0 |
| V11 | 16 | 74 | 74 | 0 |
| V12 | 32 | 219 | 207 | 12 |
| V13 | 53 | 445 | 422 | 23 |
| V14 | 72 | 490 | 455 | **35** |
| **Total** | | **2,605** | **2,535** | **70** |

All originals loaded; no stored Excel error cells found in their formula definitions. **However V14 has 35 formulas with blank caches**, so earlier descriptions of fully cached formulas were too broad. Many are designed to show blank until primary shipment evidence is available, but V14 `63_V14_Допвклад!N5:N7` should apparently display `HOLD` given the empty inputs and merits independent recalculation.

**Do not assume all 35 blanks are intentional.** Require a recalculation with supported spreadsheet engine, independent formula QA and rerun gates against synthetic and negative tests before relying on cached results.

### Additional checks required
- Compare embedded source tags, formula source comments and all currency/VAT bases.
- Test contract volume < displaced+duplicate, missing mandatory costs, negative margin and port capacity unavailable.
- Confirm the 53 inherited V13 sheets in V14 are faithful and the V7 separate 100-sheet workbook is not accidentally merged into V14.
- Do not recalculate or modify archived originals; export a new audited release.
