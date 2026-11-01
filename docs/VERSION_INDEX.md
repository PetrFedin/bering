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

| V24 | 31 Oct 2026 | Cross-check claimed ISO 6346 40ft unit identity, B/L, actual dates, source-file SHA, quantity and original V23 bytes before manual review | Physical identity engine, combined V23/V24 controller, 54 local synthetic/mock tests, [V24 evidence protocol](V24_SOURCE_IDENTITY_ADMISSION.md), [QA receipt](../quality/V24_ADMISSION_RECEIPT.json) | Draft; GitHub Actions fails before steps, original source files and authenticated consignments unavailable; P1/P2/P3 HOLD |

| V25 | 31 Oct 2026 | Correlate cargo custody events, carrier/terminal/receiver source rows, RUB invoice VAT/gross and independently identified bank settlement | [Source/settlement engine](../scripts/independent_custody_payment_v25.py), [joined gate](../scripts/release_commercial_v25.py), 144 local regression tests (90 V25 + 54 V24), 800 malformed-input mutations, [protocol](V25_CUSTODY_PAYMENT_ADMISSION.md), [QA receipt](../quality/V25_ADMISSION_RECEIPT.json) | Draft; remote Actions fails before steps, no actual authenticated paid cargo, 0/3 admitted, investment HOLD |

| V26 | 31 Oct 2026 | Verify public Magadan/FE port statistics against source, separate operator 2032 target from realized cargo, verify P1–P3 documentary readiness and diagnose runner | [Public data register](../data/public/V26_PUBLIC_SOURCE_REGISTER.json), [forecast quality gate](../scripts/public_market_forecast_v26.py), [proof intake control](../scripts/evidence_readiness_v26.py), 200 local regression tests, 1,000 deterministic malformed cases, [method](V26_PUBLIC_DATA_AND_FORECAST.md), [CI recovery](V26_CI_RECOVERY_AND_ADMISSION.md) | Draft; GitHub Research QA 314 PASS and V26 scoped QA 269 PASS + 1,000 malformed inputs on PR merge, full existing commercial gate HOLD; 0/29 independent sources, P1–P3 investment HOLD |

| V27 | 01 Nov 2026 | Acquire operator MP-1/2 exact original 2025/2026 9M XLS, separate monthly port metric from 24-month group OD and avoid fake interval forecasts | [Source intake](../scripts/v27_primary_xls.py), [24M OD gate](../scripts/v27_monthly_od_gate.py), [96 month-slot matrix](../data/od/V27_REQUIRED_COVERAGE_96.csv), 46 local tests + 400 mutations, [method](V27_EVIDENCE_AND_FORECAST_PROTOCOL.md) | Draft PR #23; monthly operator 0/24, OD 0/96, four official XLS SHA confirmed twice but encrypted; V27 local-gates GREEN 363 tests, source-parser job FAIL, 0/24 and 0/96 source-backed months, P1/P2/P3 HOLD |

## Fidelity and preservation

- Files under `archive/versions/` and `archive/workbook-extractions/` are **searchable conversions**, not replacement binary XLSX/DOCX.
- V14 carries 53 V13 sheets + 19 V14 sheets according to previous workbook audit; V13 carries V12 and so on. **Do not infer V1–V7 inclusion in V14**: V7 is a separate research track.
- Original V8–V14 source attachments are recorded with SHA-256 in `archive/FILE_MANIFEST.md`. The local [complete ZIP deliverable] may hold all local binaries, but GitHub commits must be individually verified for actual byte-preserving archive status.
- Raw V7 sources have been discovered in the project's document Library; only accessible extracted text can be preserved until binary transfer is authorized.
