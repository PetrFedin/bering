# BERING V24 · Evidence-gated 12-month cargo benchmark and source reconciliation

**As of:** 2026-10-31. **Branch:** `audit/v24-evidence-gated-forecast-20261031`; base `audit/v23-cross-pilot-cargo-integrity-20261030`.  
**Status:** research only / LOCAL_SYNTHETIC_QA_PASS / REMOTE_CI_NOT_VERIFIED / INVESTMENT_HOLD. Never merge to `main` without independent review and green checks on the same commit.

## 1. Decision and data perimeter

Forecast **unique, actually settled, net-new physical 40-foot containers** in three independent experimental routes, not the entire seaport's metric tonnes:

- **P1**: Vladivostok → Magadan, dry 40-foot.
- **P2**: Vladivostok → Magadan, reefer 40-foot.
- **P3**: China → Vladivostok → Magadan, import dry 40-foot.

P3's Vladivostok–Magadan leg cannot also become P1 demand. An incumbent group terminal diversion has no automatic new group value; see `docs/V23_CROSS_PILOT_ADDITIONALITY.md`. A benchmark does not prove carrier capacity, customer intent, contracted volumes, physical execution or debt-service ability.

## 2. Public external evidence, without invented alignment

### A. Municipality-reported port cargo, 2020–2024

Municipality of Magadan, *Итоги социально-экономического развития МО «Город Магадан» в 2024 году*, printed p.17, table “Объем переработанных грузов Магаданским морским торговым портом, тыс. т”:

| Calendar year | Thousand metric tonnes |
| --- | ---: |
| 2020 | 1,189.7 |
| 2021 | 1,254.0 |
| 2022 | 1,409.6 |
| 2023 | 1,226.6 |
| 2024 | 1,251.2 |

Source: https://magadangorod.ru/common/upload/43/editor/file/broshura_za_2024.pdf

Five-year start-to-end change: `(1251.2/1189.7 - 1)*100 = +5.17%`. This is NOT a five-year annual growth rate, seasonality estimate or group P1–P3 cohort. Definition of the named port/terminal in the municipal table needs harmonization with company filings before any year-on-year continuation beyond 2024.

### B. 2025 sources: same number, different labels — unresolved

The port authority publishes **1,834.7 thousand tonnes in 2025**, specifically for *total sea port Magadan*. Source: https://ampvanino.ru/magadan/

The Association of Sea Commercial Ports separately says **PАО MMTP had 1,834.7 thousand tonnes in 2025**. Source: https://www.morport.com/rus/news/associaciya-morskih-torgovyh-portov-pozdravlyaet-s-yubileem-generalnogo-direktora-pao

The equal numbers do **not** prove identical company/port perimeters; these claims require reconciliation against original audited company accounts and port authority handling classifications. **DO NOT append 2025 to the municipal 2020–2024 series or calculate 2025 company YoY until checked.**

### C. Published 2032 operator targets, *not independent forecasts*

PortNews (29 June 2026) reports a company's projection based on an underlying justification document NOT independently obtained here: container cargo **890.1k tonnes in 2024 → 1,000k in 2032**; coal **225.1 → 350**; general cargo **119.2 → 130**. Source: https://portnews.ru/news/393455/

Pure mathematical growth implied by those *published targets* (eight years, no validation of feasibility):
- Container tonnes: **+12.35% total**, CAGR **1.466%**.
- Coal tonnes: **+55.49% total**, CAGR **5.672%**.
- General tonnes: **+9.06% total**, CAGR **1.090%**.
- Sum of named cargo categories **1,234.4 → 1,480.0 thousand tonnes**, CAGR **2.294%**.

These are the source company's reported targets and our transparent arithmetic, NOT V24 model predictions, not project P1–P3 cargo, not TEU, not guaranteed contractual demand. We have not independently verified the underlying business justification or the completeness and non-overlap of those three cargo categories.

### D. Far East-wide 2025 context

Russia's Ministry of Transport reports **252.1 million tonnes (+6.6% YoY)** for all Far Eastern maritime ports in 2025: https://mintrans.gov.ru/eye/press-center/news/12504. It is an aggregate basin statistic, not a growth factor that can be transferred to Magadan or to the Bering project.

All source metadata and scope conflicts are stored separately at `data/public/V24_MAGADAN_PUBLIC_CONTEXT.json`; these data are **never directly used** as evidence of paid 40-foot P1–P3 shipments.

## 3. Pre-registered model and mechanical gates

`scripts/forecast_v24.py` provides an auditable **seasonal-naive reference**, not a fitted ML model and not an investment forecast.

Minimum requirements for each of P1/P2/P3:
1. At least **36 consecutive fully closed calendar months**, ending in the calendar month before the `as_of` date. This 36-month rule is a conservative design threshold for testing, NOT a scientifically established guarantee of forecast quality.
2. Each month records a nonnegative integer `paid_new_40ft`, unique month, `source_type: SETTLED_ACTUAL` and unique evidence ID. A true zero needs a reviewed, complete zero-activity register; missing months cannot become zeros.
3. Individually hashed source files, separate submitter/reviewer identities and nonfuture review dates. Byte-hash verification protects against changes but **does not authenticate financial truth, signatures, settled payment or NEW classification**. A second substantive independent review of every monthly source is still mandatory.
4. Cannot use TEU, tonnes, container turns, port throughput, forecasts or synthetic samples as declared paid physical containers.

For forecast months t+1 through t+12, `forecast[t+k] = actual[t+k-12]` (same month of prior year). The final 12 observed months are an out-of-sample historical holdout against 12 seasonal-naive guesses from the earlier history. `WAPE = sum(abs(actual - guess)) / sum(actual)`, denominator must be strictly positive.

The displayed stress-low/high values use the **minimum/maximum of 12 realized historical residuals**, clamped at zero. These are *historical sensitivity envelopes* and **NOT** probabilistic confidence or prediction intervals. This minimal baseline should be compared against other frozen baselines in a later preregistered rolling-origin exercise with more history; do not tune on the final holdout.

Decision semantics:
- `HOLD`: less than 36 months, gaps, last closed month absent, any unverified evidence or zero holdout denominator; numerical forecast `null`.
- `INVALID`: malformed periods, duplicate months or evidence IDs, partial/future months, negative/float counts, wrong unit or source type; suppress ALL pilot forecasts.
- `REVIEW`: all three pilot histories are mechanically complete and byte-reviewed, so human review of their **separate** benchmarks may begin.
- `group_forecast_40ft` ALWAYS remains `null` until a separate V23 source-level consignment matching and accounting gate is built and passed. **No code path grants investment approval**.

## 4. Actual status, reproduction, engineering blockers

The canonical versioned `data/pilots/V24_forecast_unverified.json` contains **three deliberately empty series**. This means *no verified source records available*, **NOT observed zero demand**. The official result is `HOLD`, every individual forecast `null`, group forecast `null`, investment `false`.

Local run on Python 3.13:
```bash
python3 -m unittest discover -s tests -p 'test_forecast_v24.py' -v
python3 scripts/forecast_v24.py --input data/pilots/V24_forecast_unverified.json --output v24_forecast_receipt.json
```

**20/20 synthetic tests PASS**, covering source tampering, missing evidence, non-independent reviewer, duplicate month/source, invalid unit, partial month, negative/float counts, short history, broken history and zero holdout. Local tests use fabricated text bytes *only to exercise the guards*. This is not historical forecasting performance on Magadan freight, and no source-backed P1–P3 predictive skill has been measured.

The workflow `.github/workflows/v24-forecast-qa.yml` is committed for remote CI, but GREEN is **not certified**. Prior V23 hosted runner failure happened before any job steps; the root cause is unknown. Original V20 XLSX/DOCX binaries also remain absent in GitHub, and original finance model lacks independently completed recalculation/review.

## 5. Operational path to a real decision

**Data acquisition, legally controlled:** Obtain 36+ calendar months of uniquely identified shipments, waybills, invoices, settlement proofs, OD, vessel/container identifiers, revisions/returns, contracts, agreed service dates, incumbent terminal history and actual door-to-door expenses. Source retention and privacy/access permissions must be documented; do not store sensitive customer originals in public Git history.

**Cross-pilot ground-truth:** Reconcile P1/P2/P3 and all incumbent group terminals on actual consignment keys; investigate potential duplication despite unrelated pseudonymous IDs; audit NEW versus DIVERTED and lost incumbent group contribution. Reconcile full load, cold chain, cargo class and legally available 40-foot containers.

**Economics:** Build separate RUB ex-VAT and FX scenarios, fixed/variable incremental cost, seasonal cold-chain energy, maintenance, insurance, idle and demurrage, tax and working capital, distinct unlevered FCFF and lender cases. Every numerical input needs date, source, units, scope and reviewer. No facility NPV or fundraising release may be inferred from a unit-margin screen.

**Independent evaluation:** Once records exist, hold out the latest year; calculate naive benchmark errors per route; check parameter drift, customer concentration, severe-weather/service disruptions, capacity constraints and 2025 scope reconciliation. Obtain external logistics, financial and legal sign-off.

**Investment state:** P1/P2/P3 HOLD. Standalone Magadan hub remains separate from unbuilt railway and Bering Strait crossing; neither long-distance corridor is an established freight line. For Bering, published transport statistics **cannot establish** cross-border permissions, CAPEX or signed demand.

Source ledger and outputs should be versioned, and new protected evidence should enter only through a reviewed, auditable process. Never treat a synthetic GREEN as an investment GREEN.
