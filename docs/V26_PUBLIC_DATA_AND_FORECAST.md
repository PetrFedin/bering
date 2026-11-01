# BERING V26 | Public evidence, demand guardrails and conditional forecast

**As of 2026-10-31.** This is a **research-context** note, not a feasibility study, a
bankable revenue model, an executed freight RFQ or an investment recommendation.

## Primary distinctions: unit, geographic perimeter and economic grain

1. Whole-port throughput measured in **tonnes** is not containerized tonnage.
2. Containerized cargo tonnes handled by a terminal are not TEU, 40ft physical
   containers, unique customers, origin-destination shipments or incremental cargo.
3. All cargo in the **Far Eastern basin** is a different spatial perimeter from
   cargo handled at the **Magadan seaport** or by **MMTP as an operator**.
4. A company's forward target is **not an observed realization** and is not a
   statistical forecast with a measurable confidence interval.
5. A new handling or shipping service can divert existing traffic; the genuine
   group margin increment must account for displaced activity and extra costs.

## Vetted external references

| Source ID | Period / data | Observed or target | Quality / limit |
| --- | --- | --- | --- |
| MAGADAN_SEAPORT_2025_ALL_CARGO_TONNES | 2025, **1,834,700 tonnes** | Observed, full port | Port administration official page, all cargo types and all operators, **not 40ft**: https://ampvanino.ru/magadan/ |
| FAR_EAST_PORT_BASIN_2025_ALL_CARGO_TONNES | 2025, **252,100,000 tonnes** | Observed, basin | Association of Sea Commercial Ports, published 2026-01-16; cannot assign basin growth to Magadan: https://www.morport.com/rus/news/gruzooborot-morskih-portov-rossii-za-2025-god |
| MAGADAN_MMTP_2024_CONTAINER_CARGO_TONNES | 2024, **890,100 tonnes** | Historical value cited by PortNews | PortNews 2026-06-29 citing the operator's original activity substantiation, **which has not been received**: https://portnews.ru/news/393455/ |
| MAGADAN_MMTP_2032_CONTAINER_CARGO_TARGET_TONNES | 2032, **1,000,000 tonnes** | **Operator target, not actual** | Same PortNews publication; no primary source file and no freight bookings obtained: https://portnews.ru/news/393455/ |
| MAGADAN_MMTP_2026_9M_MP1_PRIMARY_UNEXTRACTED | 2026-01 to 2026-09 | **UNKNOWN** | XLS form MP-1 listed, published 2026-10-07; raw file not downloaded; no value inferred: https://magadanport.ru/wp-content/uploads/2026/10/MP10014726.xls |
| MAGADAN_MMTP_2026_9M_MP2_PRIMARY_UNEXTRACTED | 2026-01 to 2026-09 | **UNKNOWN** | XLS form MP-2 listed, published 2026-10-07; raw file not downloaded; no value inferred: https://magadanport.ru/wp-content/uploads/2026/10/MP20014726.xls |

Primary operator report index: https://magadanport.ru/raskrytie-informacii/

**Known qualitative operational restriction:** the Magadan port administration
states that navigation is year-round but icebreaker escort is used during the
ice-formation period (December-May): https://ampvanino.ru/magadan/. This is a
**cost/schedule risk to quantify from actual quotes**. This note assigns no
invented icebreaker or reefer surcharge to P1-P3.

## What can be computed from published operator endpoints

The 2024 value and 2032 operator target concern the **same operator/container
cargo mass grain**. A smooth *illustrative* constant-growth interpolation is:

```
CAGR = (1,000,000 / 890,100) ** (1 / (2032-2024)) - 1
     = 0.014659088703... = 1.4659% per year
Smooth(year) = 890,100 * (1+CAGR) ** (year-2024) tonnes
Flat(year)   = 890,100 tonnes (no-growth what-if counterfactual)
```

| Year | Smooth path, tonnes | Flat, tonnes | Classification |
| --- | ---: | ---: | --- |
| 2024 | 890,100 | 890,100 | Historical figure **reported** from operator document |
| 2025 | 903,148 | 890,100 | Arithmetic interpolation, **not actual** |
| 2026 | 916,387 | 890,100 | Arithmetic interpolation, **not actual** |
| 2027 | 929,821 | 890,100 | Arithmetic interpolation, **not actual** |
| 2028 | 943,451 | 890,100 | Arithmetic interpolation, **not actual** |
| 2030 | 971,314 | 890,100 | Arithmetic interpolation, **not actual** |
| 2032 | 1,000,000 | 890,100 | Operator target for smooth path, **not achieved** |

Endpoint difference: **109,900 tonnes** over eight years; straight-line arithmetic
average **13,737.5 tonnes per year**. **These values are not Bering's additional
cargo, and tonnes have NOT been converted to 40ft units.** No current primary
2025/2026 annual actual for operator container cargo has been extracted for
proper model validation, seasonality, forecast bias or backtesting. As a result
**prediction intervals, scenario probabilities, and 2026 actual vs target gaps
cannot be estimated responsibly**.

## Project-specific required equation (from V23)

For each independently verified **unique economic shipment** in the same group:

```
NEW      : Q_40ft * CM_new_per_40ft
DIVERTED : Q_40ft * (CM_new_per_40ft - CM_incumbent_group_per_40ft)
Group incremental CM = sum(unique changes) - extra fixed operating cost - extra risk cost
```

Claims of extra paid containers, group incremental margin, project NPV, ROI,
pricing or a bankable forecast remain **NULL/HOLD** until the same document
chain is reconciled across carriers, actual terminals, consignors, consignees,
invoices, bank settlements and the 24-month historical multi-terminal OD base.

**No estimate of Bering demand or project revenue is permissible from these
public market aggregates alone.** Route-level 40ft observations and binding
customer purchase decisions have not been received.

## Scope of scripts and operational admission

- `data/public/V26_PUBLIC_SOURCE_REGISTER.json`: six reviewed metadata slots,
  three observed/reported historic values, one forward target and two source
  listings without extractable values. Cited URLs are fixed and kept auditable.
- `scripts/public_market_forecast_v26.py`: tests metric grain, nullness,
  provenance tier and formulas; outputs `PUBLIC_CONTEXT_ONLY` and keeps
  `commercial_gate=HOLD` even when source metadata is structurally valid.
- `data/pilots/V26_EMPTY_PROOF_INTAKE.json`: 29 missing proof categories across
  P1/P2/P3; a **document readiness count** only.
- `scripts/evidence_readiness_v26.py`: checks local file hash, confinement,
  independent reviewer, date and category coverage. Full coverage advances to
  **manual external authenticity review**, never investment PASS.
- `scripts/offline_qa_v26.py`: repeatable free local regression suite; its
  `github_actions_green` flag remains false and it must never be cited as a
  remote GitHub-hosted CI result.

## Evidence collection sequence

1. Obtain and locally SHA-256 verify the 2026 9-month original MP-1/MP-2 XLS
   files through an authorized source channel; audit field labels, scope,
   period, units, duplicates and the 2025 like-for-like comparable. Commit a
   **source manifest**, not confidential originals without legal permission.
2. Request genuine P1/P2/P3 route-level monthly OD data for >=24 comparable
   months, measured in exact 40ft units with actual load condition and
   payload weight. Reconcile across all incumbent operators and terminals.
3. Collect *original* customer order, D2D written quote, waybill, actual
   loading/delivery, bank-confirmed settlement, group margin and downstream
   costs; P2 requires temperature/power evidence and P3 customs/feeder evidence.
4. Run V23→V25 cross-pilot controls and the V26 source readiness gate;
   investigate overlaps manually. Independently verify contract authenticity
   and incremental profitability. Not one category can be marked actual paid
   cargo from a copied PDF or a guessed external ID alone.
5. Resume Actions on the **same pinned SHA** only once hosted-runner failure
   is resolved; obtain logs, review and protection on main, then consider
   integration under separate approved PRs.

**Commercial:** P1 HOLD / P2 HOLD / P3 HOLD. **Investment:** HOLD.
