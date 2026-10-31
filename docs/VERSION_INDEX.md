# Research version index

| Stage | Date | Primary question | Material | Status |
|---|---|---|---|---|
| V1–V6 | 2026, earlier | Scenario foundations, engineering, regional statistics | Historic sheets reportedly embedded in V7 workbook (81 sheets V6) | Original stand-alone binaries **not verified in repo** |
| V7 | 23 Oct 2026 | Life-cycle costs, reliability, safety, time value of capital | Library text and workbook extraction | Historical research |
| V8 | 24 Oct 2026 | The network gaps, Magadan–Yakutia dependencies | Article + model | Archived research |
| V9 | 25 Oct 2026 | Freight OD economics and cargo demand evidence | Article + model + register | Archived research |
| V10 | 25 Oct 2026 | China–Magadan–Alaska network and hubs | Article + model + network diagram + register | Archived research |
| V11 | 25 Oct 2026 | 30 commercial cards, shippers, contracts | Article + model + two CSV registers | 0 proven new-rail contracts |
| V12 | 25 Oct 2026 | SASCO, port tariffs, transport charges and RFQs | Article + model + rate and RFQ CSV | Public rates, no complete D2D |
| V13 | 26 Oct 2026 | D2D, capacity, investor proposal, Magadan pilot test | Article + 53-sheet model + 3 registers | Commercial evidence HOLD |
| V14 | 26 Oct 2026 | Waybills, invoices, payments, new cargo, extra margin | Report + RFQ drafts + 72-sheet model + 2 registers | **0/3 pilots admitted; 15 RFQs not sent** |
| V15 | 27 Oct 2026 | Evidence-backed three-pilot admission gates | Commercial scripts, JSON inputs, test harness | Committed to main; GitHub Actions FAILED |
| V16 | 27 Oct 2026 | 30 objective criteria for an evidence-bound 8.5–9 target | 6-axis rubric, baseline, defect log | Draft PR #8; not merged |
| V17 | 27 Oct 2026 | Independent quality rules and finance test architecture | Quality engine, OOXML integrity, scientific protocol | Draft PR #9; not merged |
| V18 | 27 Oct 2026 | External source hashes and reviewer separation for pilot cargo | Hardened document gate, 20 local regression tests | Draft PR #9; not merged |
| V19 | 27 Oct 2026 | Source-byte preservation and release packaging | Local 31-file originals + SHA archive, no GitHub binary import | Local only |
| V20 | 28 Oct 2026 | Financial arithmetic reproducibility and source integrity | Independent 223-output tie-out, 12+6 tests, 42-file import pack | Draft PR #11; CI and original binary upload still BLOCKED |

| V21 | 29 Oct 2026 | Fail-closed integrity of Excel formula lineage and proof that original files are actual Git blobs | Formula fingerprint 493/493, 42-file SHA list, 13 specialized local tests, conditional admission workflow | Draft; original XLSX/DOCX not uploaded to GitHub; Actions BLOCKED |

| V22 | 30 Oct 2026 | Safe source ZIP importer with explicit rights/privacy approval and failure tests | Python importer, 21 synthetic fixture tests, isolated Actions workflow, [import protocol](V22_ORIGINALS_IMPORT_PROTOCOL.md) | Topic branch only; real originals not imported; runner and investment HOLD |

| V23 | 31 Oct 2026 | Prevent duplicate economic shipments, consignment IDs and shared costs across P1/P2/P3; reconcile each pilot's new volume and incremental group margin | [Cross-pilot engine](../scripts/cross_pilot_additionality_v23.py), [combined decision gate](../scripts/release_commercial_v23.py), 32+16 local synthetic tests, [method](V23_CROSS_PILOT_ADDITIONALITY.md), unverified zero-claim input and CI smoke | Draft, remote CI not certified; 0/3 pilots admitted; investment HOLD |

| V24 | 31 Oct 2026 | Evidence-backed forecasting: official 2020–2024 series vs unaligned 2025, 36-month actuals prerequisite, frozen 12-month seasonal-naive holdout benchmark | [Forecast module](../scripts/forecast_v24.py), [method/source review](V24_EVIDENCE_GATED_FORECAST.md), 20 synthetic regression tests, canonical no-claim JSON and machine-readable receipt | Draft, 20/20 local synthetic PASS only, P1/P2/P3 actual forecast HOLD, no source contracts/CI/investment approval |

## Fidelity and preservation

- Files under `archive/versions/` and `archive/workbook-extractions/` are **searchable conversions**, not replacement binary XLSX/DOCX.
- V14 carries 53 V13 sheets + 19 V14 sheets according to previous workbook audit; V13 carries V12 and so on. **Do not infer V1–V7 inclusion in V14**: V7 is a separate research track.
- Original V8–V14 source attachments are recorded with SHA-256 in `archive/FILE_MANIFEST.md`. The local [complete ZIP deliverable] may hold all local binaries, but GitHub commits must be individually verified for actual byte-preserving archive status.
- Raw V7 sources have been discovered in the project's document Library; only accessible extracted text can be preserved until binary transfer is authorized.
