# Bering V27 - primary XLS intake, 24-month OD and non-bankable stress envelopes

Date: 2026-11-01. Status: RESEARCH_ONLY / INVESTMENT_HOLD.

## Verified source boundary

The official [Magadan MMTP disclosure index](https://magadanport.ru/raskrytie-informacii/) lists MP-1 and MP-2 XLS disclosures for 9 months of 2025 (published 2025-10-08) and 9 months of 2026 (published 2026-10-07). Four exact URLs are pinned in `data/public/V27_PRIMARY_SOURCE_REGISTER.json`. The official [client page](https://magadanport.ru/klientam/) separately offers a monthly series of **available capacity** XLS files: these do **not** establish actual handled cargo, utilization or demand.

An XLS publicly posted by the operator is a company-specific disclosure. Neither the port basin's annual tonnage nor this operator's 9-month XLS can directly supply verified monthly 40ft container OD, signed incremental Bering cargo or actual customer payments.

## Acquisition protocol

`python scripts/v27_primary_xls.py --output-dir v27_review --require-all --save-originals` may run only with internet access and after installation of the read-only XLS parser `xlrd==2.0.2`. It:

1. Allows HTTPS downloads only from the official Magadan port disclosure upload path and refuses off-origin redirects;
2. Rejects oversized files and anything lacking the OLE compound document magic bytes;
3. Logs exact SHA-256, byte length, individual worksheet dimensions and potential label-cell coordinates;
4. Keeps XLS bytes **transiently on the GitHub hosted runner only**; prints SHA-256 and candidate cell coordinates in the job log and step summary. **No Action artifact upload is used** because V27 first CI run encountered `Artifact storage quota has been hit`. The raw XLS bytes are **not preserved in GitHub**. An authorized, rights-reviewed byte-preserving transfer is still required before a permanent research archive;
5. Does not execute Excel macros/formulas and **accepts zero numerical metrics automatically**. Rows are candidate source evidence, not certified cargo tonnage.

A failed source download is a **failed acquisition job**, separate from the code's quality-test status. Do not mark source verification GREEN merely because the synthetic regression job is GREEN.

An independent reviewer must open the original file, document cell coordinates, source units, time period (9M cumulative vs month), operator/legal scope and exact URL/SHA, and compare with prior-year equivalently defined indicators. Do not derive a month by dividing a 9-month total by nine. Two quarterly cumulative differences can represent a *quarterly* flow only after verifying cumulative definitions and revisions, never a precise individual month.

## 24-month actual OD: required grain

For the 24 **completed** calendar months 2024-10 through 2026-09:

- `data/od/V27_REQUIRED_COVERAGE_96.csv` enumerates **72 pilot-month evidence requests** (24 each for P1, P2 and P3) plus **24 incumbent-group-month evidence requests**. Rows are empty on purpose, tagged MISSING_NOT_ZERO.
- `data/od/V27_GROUP_24M_UNVERIFIED.json` is the signed/independently verified source *intake*, initially empty. 0 supplied records != 0 actual freight.
- One shipment source row represents one physical 40ft unit with a pseudonymous economic group, OD pair, container number, document-row locator and exact file digest. Double counted shipment IDs and duplicated physical units across lanes in the same month are rejected. Year and month must be genuine observations.
- Every lane-month must have an independently attested coverage statement, including months with actual **documented zero**. No implicit data smoothing, duplicated file-row accounting, PDF-to-payment inference or guessed tonnes/TEU-to-40ft conversion.
- Existing-group lanes need a complete 24-month source baseline to demonstrate cannibalization/transfer rather than falsely calling old cargo new.

A real 24-month raw OD set requires shipper/consignee legal identity (pseudonymized in Git), container ISO number, cargo, OD, actual departure/arrival, terminal, source institution, invoice and bank reference, net group contribution and incumbent group margin. The V27 intake does not claim to authenticate those entities; separate V23/V24/V25 compliance reviews remain mandatory.

## Projection rule (do not mistake for confidence intervals)

Only when **all 96 source-attested lane-month cells** have matching underlying unique shipment rows, valid independent reviewer and matching file SHA, the code constructs a **12-month historical-delta stress envelope** for the three pilot-route observed monthly volumes:

- Let `A_m` be the month `m` from year 1, `B_m` the same month in year 2, `d_m = B_m - A_m` across the twelve seasonal month pairs.
- For each future month `m`, a LOW/CENTRAL/HIGH scenario is `max(0, round(B_m + min/median/max(d_1...d_12)))`. The calculation uses exact Decimal and rounds container quantities to integers.
- The resulting `next_12_month_total_40ft` is a *mechanical historical stress range*. It is **not** a probabilistic 5%-95% interval, an econometrically calibrated forecast, a commercial order, or a projection of Bering revenue.
- Even on complete data, V27 reports at most `REVIEW_BASELINE_ONLY` and always `eligible_to_forecast_Bering_revenue=false`, `investment_approved=false`. External source authenticity and true causal group additionality must be proven separately.

Two full years are insufficient to establish stable long-run seasonality and capital project traffic with statistical confidence. More years, operator restrictions, alternative routes, customer demand elasticity, service reliability and seasonally distorted years will be needed before projecting Bering investment throughput.

## Reproduce and status

```bash
python -m unittest discover -s tests -p 'test_v27_*.py' -v
python quality/fuzz_v27.py
python scripts/v27_monthly_od_gate.py \
 --operator-monthly data/public/V27_PORT_MONTHLY_UNVERIFIED.json \
 --od-24m data/od/V27_GROUP_24M_UNVERIFIED.json \
 --out v27_baseline_receipt.json
```

Expected default: port monthly 0/24, OD 0/96, both **HOLD**, `projection=null`, `investment_approved=false`. The separate primary XLS acquisition job is explicitly **not** a substitute for these data categories.

Next hard blockers: rights-screened original historical Bering spreadsheets V20-V21, verified 24-month shipper and incumbent group data, genuine signed new freight, carrier/terminal/recipient acceptance, priced quotes, actual bank settlement and independent financial/security review. Main and funding remain HOLD.

## 1 Nov 2026: GitHub Actions artifact quota incident

First V27 PR CI run [41349929715](https://github.com/PetrFedin/bering/actions/runs/41349929715) **executed 351/351 repository regression tests** and all HOLD controls passed. The otherwise-successful local-gates job failed on the final artifact upload with exact GitHub log error: `Failed to CreateArtifact: Artifact storage quota has been hit`; as a result the dependent source acquisition job was **SKIPPED**. This does **not** prove a public XLS download failure.

A revised V27 workflow removes both artifact-upload steps and retains source SHA/worksheet candidates in job logs and the GitHub Step Summary (at no additional artifact storage charge). The public XLS acquisition must be independently rerun and its status verified; the prior unsuccessful run does not establish source bytes.

## 1 November 2026: public original bytes found, spreadsheet contents still encrypted

Two independently executed GitHub-hosted retrievals downloaded all four public OLE ` .xls sources from the officially disclosed MMTP URLs and produced stable exact original SHA-256 values, sizes and OLE header checks:

| Original | Original bytes | SHA-256 | Reader result |
|---|---:|---|---|
| MP1_2026_9M | 267,264 | `20f684ee23777db318d2dda4942891d8a7ee57e43140fe0c0c47d767893f61a2` | `Workbook is encrypted` |
| MP2_2026_9M | 923,136 | `11afb90722824351676e8c2d800c8bee71564fec5d66bf3234149659c9e36a42` | `Workbook is encrypted` |
| MP1_2025_9M | 259,584 | `ba8c378d15ef70273ecd54d75463f98928ab73387fbe85be20a207ddc88254aa` | `Workbook is encrypted` |
| MP2_2025_9M | 893,952 | `288ef40904064f29884375072fc7a0619f1522a00809c069217c28ff9d37e294` | `Workbook is encrypted` |

Verified action runs: [run 41350323889](https://github.com/PetrFedin/bering/actions/runs/41350323889) and [run 41350390175](https://github.com/PetrFedin/bering/actions/runs/41350390175). **These raw bytes were held temporarily only by GitHub runners, NOT committed as XLS binaries**. The repository [source register](../data/public/V27_PRIMARY_SOURCE_REGISTER.json) now pins the exact 4 original checksums. V27 source loader rejects any unexpected future file-byte change. XLS parsing is NOT complete, no operator metric has been accepted, and none of the four sources proves any monthly OD or Bering cargo. Independently obtaining legally authorized unencrypted primary materials remains necessary.
