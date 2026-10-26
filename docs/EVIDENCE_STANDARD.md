# Data provenance and commercial acceptance

## Evidence classes
| Class | Meaning | Eligible for bankable revenue? |
|---|---|---|
| A0 | Executed enforceable transport contract + proof of payments/actual use and independently demonstrated incrementality | Potentially, after legal/credit/capacity review |
| A1 | Signed binding offtake or take-or-pay with commercial and jurisdictional validity | Potentially, after covenant/conditions analysis |
| B | Company annual report, statutory report, actual published traffic/tonnage, official tariff and terms | No by itself |
| C | Carrier published schedule and price, project statement, permit / investment deck | No |
| D | Researcher comparison, test scenario, hypothetical rate, P50/P90 sensitivity | Never as observed data |
| U | Missing / cannot verify / conflicting | Never |

## Canonical commercial OD record
```json
{
  "od_id": "P1",
  "owner": null,
  "customer": null,
  "product_code": null,
  "origin_site": null,
  "destination_site": null,
  "route_leg_ids": [],
  "unit": "40ft container",
  "actual_shipments_24m": null,
  "contracted_future_shipments": null,
  "quote_ids": [],
  "published_rate_ids": [],
  "actual_waybill_ids": [],
  "invoice_ids": [],
  "proof_of_payment_ids": [],
  "legal_gate": "UNVERIFIED",
  "port_capacity_gate": "UNVERIFIED",
  "new_volume": null,
  "diverted_volume": null,
  "duplicate_volume": null,
  "group_incremental_margin": null,
  "investment_gate": "HOLD"
}
```

## Calculation
`new_volume = max(0, contracted_future - diverted_from_existing - duplicated)`; however, **do not calculate a nonzero new volume until all three inputs are backed by independent documents**.

`group_incremental_CM = new_volume * CM_new + diverted_volume * (CM_new - CM_old) - incremental_fixed_OPEX - additional_risk_costs`.

`D2D = pickup + on_carriage + linehaul + handling_not_included + customs + storage + insurance + last_mile + expected_losses + equipment + VAT_effect`.
If any mandatory leg unknown, **D2D = UNKNOWN**, not sum of partial known charges.

## Reject conditions
- Carrier quote on a different week/Incoterm/container ownership/weight, or VAT basis cannot be normalized.
- Price bundle's included handling/fees already counted separately.
- Counterparty unclear, evidence older than its valid period, redaction prevents required cross-check.
- Sales attributed to project but actually reallocated from existing group terminal.
- Total contracted < diverted + duplicated volume, negative margin without repair, currency mismatch, unit mismatch.
- Missing port capacity, sanctions/export permission, Indigenous consultation / environmental approvals required for site.

## Provenance
Every observation needs `source_id, source_url, publisher, publication_date, accessed_date, observation_period, region, metric, unit, tax_basis, value, scope, evidence_class, limitations, sha256_if_local`.

**Conflicting records must both be retained** with an explicit reconciliation ticket rather than overwritten. Historic assumptions remain tagged as model scenarios.
