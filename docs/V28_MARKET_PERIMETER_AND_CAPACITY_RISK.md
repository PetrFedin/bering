# Bering V28 - Magadan market perimeter and versioned terminal-capacity claims

**Source review checkpoint: 1 November 2026.** Software stage prepared 2 November 2026. This is research; never a traffic, payment, bankability, or investment certification.

## Evidence and intended grain

| Metric ID | Geography / owner | Period | Reported value | Data unit | Source and interpretation |
|---|---|---|---:|---|---|
| MAGADAN_ALL_PORTS_2024_TEU | All Magadan port terminals | 2024 calendar year | 80,900 | TEU (twenty-foot-equivalent units) | https://www.finmarket.ru/news/6331647 , 28 Jan 2025, relaying a Morcenter report |
| MAGADAN_ALL_PORTS_2025_TEU | All Magadan port terminals | 2025 calendar year | 84,300 | TEU | https://morvesti.ru/news/1679/120254/ , 2 Feb 2026, relaying Morcenter |
| MMTP_OPERATOR_2025_TONNES | PAO Magadan MTP, a specific terminal operator | 2025 calendar year | 1,834,700 | tonnes of all cargo | https://www.morport.com/rus/news/associaciya-morskih-torgovyh-portov-pozdravlyaet-s-yubileem-generalnogo-direktora-pao , 18 May 2026; association statement |

The descriptive 2024-to-2025 difference in **the whole-port TEU series** is 84,300 - 80,900 = **3,400 TEU**, or **4.20%** using unrounded values. It is not a 2026 or future forecast. Neither TEU nor all-cargo tonnes can be converted to unique physically loaded 40ft containers absent 20ft/40ft composition, loaded/empty, moves, and transaction-level evidence. The operator figures are at a different entity perimeter from the whole-port statistics. The original Morcenter data file and exact methodology have **not** been authenticated here; both TEU data points rely on secondary published reports.

## Another Magadan Marine Logistics Centre: conflicting published design versions

The two publications concern the named Marine Logistics Centre Magadan, with the published developer **OOO Morskoy Logisticheskiy Tsentr**. However, the extent to which the published scopes and stages correspond is still unverified.

- 14 May 2026 initial / 25 May updated [Roscongress regional investment-card](https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/): **30,000 TEU/year design capacity**, 150,000 tonnes/year general cargo, 200,000 tonnes/year fish products. The same project card displays **RUB 37.7bn** budget and indicative **21% IRR / RUB 57.4m NPV**, which remain *promoter-published parameters, not independently reviewed financial-model results*. Do not import them into Bering.
- 1 October 2026 [Russian State Expertise Agency announcement](https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e): first-stage engineering design and survey documents received a **positive expert review**. Project **announced** annual capacity now up to **150,000 TEU**, 200,000 tonnes fish products and over 40,000 tonnes general cargo. No commissioning or occupied capacity has been established by this announcement.

**Source conflict:** 150,000 / 30,000 = **5.00x** the earlier TEU claim; this is not growth in actual throughput, not five independent facilities, and not 180,000 TEU of cumulative new capacity. It may be a changed design, scope, step, or media presentation; an approved versioned engineering scope and contractor explanation are still needed. These competing forecasts have vastly different consequences for pricing and group transfer assumptions.

**Critical separation:** 2025 observed port flow = 84,300 TEU. October 2026 projected capacity of another facility = 150,000 TEU per year. Comparisons between one year's existing flow and a future facility's design capacity DO NOT establish market demand, excess capacity, committed shipments, time of commissioning, or market share for Bering.

## Risk register and decisions

| Severity | Issue | Why material to Bering | Required evidence |
|---|---|---|---|
| CRITICAL | No authenticated new paid P1/P2/P3 shipments, B/L, OD or banking and group displacement | Commercial margin can be entirely transferred rather than incremental | 24-month shipper-level and group-level OD, independently verified contracts, receipts, paid invoices, full group margin waterfall |
| HIGH | Potential external terminal's May vs October TEU design discrepancy | Competition / substitutability / timetable and investment perimeter cannot be compared | Signed design change record, approved phase boundaries, terminal developer, capacity in service vs only planned |
| HIGH | Whole-port annual TEU mixed with operator cargo tonnes | Dimensional error can inflate market volumes and project projections | Keep separate entity, period, grain and unit; original Morcenter methodology and port statistics |
| HIGH | Encrypted official MMTP MP1/MP2 originals | Nominal public publication does not yield extractable audited monthly cargo data | Officially readable copies, source hashes, documented cell mappings and source rights |
| MEDIUM | Container capacity reports on MMTP website describe **available** capacity, not physical movement | Available capacity cannot prove utilization or 40ft new shipments | Operational terminal-gate/manifest shipment records and independently confirmed receipt |

## Technical changes

- [Versioned market registry](../data/public/V28_MAGADAN_MARKET_PERIMETER.json) preserves units, periods, legal/project identity, source URLs, published status and verification flags.
- [Market-perimeter validator](../scripts/v28_market_perimeter.py) rejects duplicate IDs, unreviewed source changes, future dates, untrusted source URLs, TEU-to-40ft conversion, capacity summation, forged commissioning and market-to-revenue promotion.
- [Read-only combined release gate](../scripts/v28_group_decision.py) checks the same V28 source snapshot alongside V27 24-month operator/OD, V26 document intake and V25 commercial/custody/payment decisions. Any source change during evaluation invalidates the result. **HOLD remains the only permitted business status** for the current empty evidence baseline.
- [Research-only CI](../.github/workflows/v28-market-and-commercial-readiness.yml) runs repository regressions, negative-source tests, a deterministic corruption probe, V28 source checks and the actual V25-V28 combined HOLD gates on one GitHub PR SHA. No artifact upload (GitHub artifact quota has been hit before).

Reproducibility commands from GitHub PR checkout:

```bash
python -m unittest discover -s tests -v
python quality/fuzz_v28.py
python scripts/v28_market_perimeter.py --register data/public/V28_MAGADAN_MARKET_PERIMETER.json
python scripts/v28_group_decision.py --repo .
```

### Actual remaining evidence blockers

1. Original published MP1/MP2 files were received four times by GitHub runner with identical bytes, but **all remain encrypted** and the accepted original metric count is zero. Hashes are in `data/public/V27_PRIMARY_SOURCE_REGISTER.json`. Original binaries and the historic 42-file archive have not been preserved in GitHub.
2. The 24-month operator-specific cargo panel has **0/24 verified monthly observations**. The OD collection matrix for P1, P2, P3 and the existing group has **0/96 reviewed monthly slots**. These are missing-document counts, not measured zero cargo.
3. No independently verified project commissioning date or scope of the 30k/150k TEU Magadan MLC design discrepancy.
4. No source-backed 2026 annual container throughput; no tax-equivalent D2D rate, proven incremental group CM, verified new physical 40ft load, or bank origin settlement.
5. GitHub main is not protected; do not merge the version chain without CI, PR review and reliable evidence.

**Investment decision remains HOLD. No signed Bering new cargo, bankable group revenue, forecast or return is admitted.**
