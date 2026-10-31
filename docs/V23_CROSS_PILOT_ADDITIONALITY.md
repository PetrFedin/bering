# BERING · V23 — cross-pilot cargo additionality

**Date:** 2026-10-31. **Branch:** audit/v23-cross-pilot-cargo-integrity-20261030.  
**Release:** DRAFT / LOCAL_SYNTHETIC_TESTS_PASS / REMOTE_CI_HOLD / INVESTMENT_HOLD.

## Purpose

Prevent a physical or economic shipment from being reported twice as incremental cargo or twice as group contribution margin when it crosses several routes or terminals.

The project has **three research-only pilots**:

- **P1:** dry 40ft, Vladivostok → Magadan.
- **P2:** refrigerated 40ft, Vladivostok → Magadan.
- **P3:** import dry 40ft, China → Vladivostok → Magadan.

The Vladivostok → Magadan leg of P3 **must not** be included again as stand-alone P1 freight. Nor may a physical shipment and a transshipment/handling event become separate incremental cargo.

## Grain and financial method

**Grain:** a unique economic shipment, linked to a unique physical consignment and one pilot; not route leg, TEU, tonnes or terminal operations. No shipment IDs are inferred from date or weight alone.

For each classified shipment:

- **NEW:** quantity × new group unit contribution margin.
- **DIVERTED:** quantity × (new group unit contribution margin − incumbent group unit contribution margin).
- **EXCLUDED:** zero included in the screening model, with documented exclusion reason.
- **Per-pilot:** sum distinct shipment incremental margins less incremental fixed operating expense and incremental risk cost, each charged once.
- **Group:** sum P1+P2+P3 only when all pilot inputs are numerically complete and there are no structural errors.

Amounts are computed using Decimal (not floats), in RUB **ex-VAT** to 0.01 RUB. No silent FX or VAT normalization is allowed. A negative pilot margin is HOLD, not proof of investability.

This quantity is only a **screening group contribution margin change**, not company revenue, NPV, profit after tax, FCFF or actual cash receipt. Displaced group earnings are subtracted for diverted cargo, not relabeled new freight.

## Implemented controls

1. Duplicate economic shipment IDs are rejected case-insensitively across all three pilots.
2. Duplicate physical consignment keys are rejected across all three pilots even when economic IDs differ.
3. Duplicate fixed-cost or risk-cost event IDs across pilots are rejected; no undocumented allocation percentages are assumed.
4. Each shipment requires pilot, compatible cargo class, one economic group, period and consistent currency/tax basis.
5. NEW cannot claim pre-existing group service/margin, while DIVERTED requires incumbent service identity and unit margin.
6. Missing quantity, contribution or cost yields **null**, not zero. A fictitious zero with missing evidence is HOLD.
7. Evidence integrity checks require distinct source IDs for contract, waybill, payment, 24-month baseline, additionality and unit contribution; SHA-256 source-byte verification, independent submitter/reviewer and non-future review dates.
8. Source integrity does **not** authenticate signatures or payments or prove that freight is genuinely incremental. This requires independent substantive review.
9. Full synthetic evidence can lead to at most REVIEW; no code path produces commercial PASS or bankable revenue approval.
10. Any structural error invalidates the group total (INVALID), blocking dissemination of an apparently exact but duplicated figure.

## Files and execution

- [Engine](../scripts/cross_pilot_additionality_v23.py)
- [32 synthetic regression tests](../tests/test_cross_pilot_additionality_v23.py)
- [Unverified baseline JSON](../data/pilots/V23_cross_pilot_unverified.json) — zero source shipments deliberately, and cost-event identifiers are *structural placeholders only*.
- [CI workflow](../.github/workflows/v23-cross-pilot-qa.yml)
- [Machine-readable QA receipt](../quality/V23_ADMISSION_RECEIPT.json)

Execute from repository root:

~~~bash
python -m unittest discover -s tests -p 'test_cross_pilot_additionality_v23.py' -v
python scripts/cross_pilot_additionality_v23.py \
  --input data/pilots/V23_cross_pilot_unverified.json \
  --output v23_cross_pilot_screening.json
~~~

The unverified baseline must produce HOLD, zero actual source records, three pilots HOLD and a null group margin. This is the intended data-quality verdict, not evidence of actual zero demand.

Supply --evidence-index **together** with --evidence-dir for externally reviewed materials outside Git if documents contain confidential information. With --require-review, incomplete HOLD exits 3; structurally invalid input exits 2. REVIEW **still requires** independent external commercial assessment.

## Local synthetic testing

32/32 automated unit tests passed locally on Python 3.13.5. Checks include shipment overlap, consignment duplication, duplicated cost event, absent 24-month baseline, tampered document, non-independent reviewers, inconsistent FX/VAT, lost incumbent margin, invalid monetary precision, excluded items, future-dated data, missing cost and output exit codes.

An *entirely synthetic* screening example, not a freight forecast:

- P1 = 2 × 100 − 10 − 5 = **185 RUB**.
- P2 = 1 × (200 − 120) − 10 − 5 = **65 RUB**.
- P3 = 1 × 50 − 5 − 5 = **40 RUB**.
- Group = 185 + 65 + 40 = **290 RUB**.

**These numbers and generated evidence documents are synthetic test fixtures only.** Never describe 290 RUB as actual revenue, customer commitments or any validated tariff.

## Current blockers

- The actual original P1–P3 pilot input JSON files contain no verified contracts, waybills, payments or actual group volume evidence.
- The canonical V23 cross-pilot input contains **zero** actual shipments because no individual source waybills have been supplied.
- Real V20 source XLSX/DOCX binaries have not been committed to GitHub; V22 importer did not remedy the missing source archive.
- Last runner check for V22 failed before first step. V23 remote GitHub CI and independent review are **not yet certified**.
- Two shipments with unrelated invented keys might still be the same physical cargo. This control **cannot** detect forged identifiers without third-party linkage across original waybills, dates, counterparties, containers and incumbent terminals.
- The 24-month group OD baseline, independently validated recurring commitments and actual total D2D costs remain absent.

## Commercial admission criteria

1. Collect real, dated OD, waybill, invoice, payment and 24-month multi-terminal baseline under authorized privacy controls.
2. Assign canonical shipment IDs and reconcile actual physical cargo across P1, P2, P3 and all incumbent group terminals.
3. Independently review the substantive truth of contract and shipment evidence, unit contribution and incremental group costs.
4. Run original commercial pilot gates plus the cross-pilot V23 calculation. Any structural conflict blocks all pilot investment claims.
5. Obtain external financial/legal review before any committee decision. The engine never approves funding.

**Decision:** P1/P2/P3 = HOLD; no bankable incremental freight proven. The international rail and Bering crossing remain research scenarios.
