#!/usr/bin/env python3
"""V29 fail-closed published-claim stage guard. No commercial or investment admission.

All pinned statements are externally published claims, not primary design
documents, paid waybills, or proof of the physical commissioning of an MLC.
The frozen register is versioned: changes to its claims need a reviewed new
version, not silent replacement of the evidence baseline.
"""
import argparse
import json
from pathlib import Path

CLAIMS = {
    "MLC_MAY_2026_30000_DESIGN": (
        "MLC_MAGADAN_COMPETITOR", "ANNOUNCED_DESIGN_CAPACITY",
        "INVESTMENT_CARD", "CONTAINER_DESIGN_CAPACITY", "TEU_per_year",
        "30000", "2026-05-25",
        "https://investinregions.ru/projects/morskoy-logisticheskiy-tsentr-magadan/"
    ),
    "MLC_OCT_2026_150000_DESIGN": (
        "MLC_MAGADAN_COMPETITOR", "ANNOUNCED_DESIGN_CAPACITY",
        "POSITIVE_DESIGN_EXPERTISE", "CONTAINER_DESIGN_CAPACITY",
        "TEU_per_year", "150000", "2026-10-01",
        "https://egrz.ru/organisation/news/be268787-74bd-f111-80ff-00505634024e"
    ),
    "MLC_PORTFOLIO_150000_DESIGN": (
        "MLC_MAGADAN_COMPETITOR", "THIRD_PARTY_PROJECT_DESCRIPTION",
        "UNDATED_PROJECT_PORTFOLIO", "CONTAINER_DESIGN_CAPACITY",
        "TEU_per_year", "150000", None, "https://terramaris.ru/prom"
    ),
    "MLC_REGIONAL_2030_PLANNED_YEAR": (
        "MLC_MAGADAN_COMPETITOR", "REGIONAL_PROJECT_PLAN",
        "REGIONAL_STRATEGY_2030", "PLANNED_COMMISSIONING_YEAR",
        "year", "2030", "2026-04-30",
        "https://base.garant.ru/414156851/da0ca740e319b67eff630b4065586e13/"
    ),
    "MMTP_NOV_2026_AVAILABLE_CAPACITY_LIST": (
        "MMTP_EXISTING_PORT_OPERATOR", "DOCUMENT_AVAILABILITY_ONLY",
        "OPERATOR_WEBPAGE", "AVAILABLE_CAPACITY_REPORT_LISTED",
        "document_presence", None, None, "https://www.magadanport.ru/klientam/"
    ),
}
PINNED_FIELDS = (
    "entity_scope", "claim_class", "stage", "measure", "unit",
    "value", "source_date", "source_url"
)
CLAIM_FIELDS = set(PINNED_FIELDS) | {
    "id", "source_qualification", "source_document_bytes_authenticated",
    "physical_commissioning_verified", "actual_paid_bering_cargo_verified"
}
CONTROL_FIELDS = {
    "design_versions_reconciled": False,
    "commissioned_capacity_verified": False,
    "actual_paid_bering_cargo_verified": False,
    "monthly_actual_operator_cargo_verified": False,
    "never_sum_design_versions": True,
    "never_promote_planned_year_to_actual": True,
    "never_equate_available_capacity_and_throughput": True,
    "investment_approved": False,
    "bankable_revenue_approved": False,
}

def evaluate(data):
    """Reject modified source perimeter; never treat withheld evidence as zero."""
    errors = []
    if not isinstance(data, dict):
        data = {}
        errors.append("Register is not a JSON object")
    if set(data) != {"schema", "as_of", "purpose", "claims", "controls"}:
        errors.append("Unknown or missing register fields")
    if data.get("schema") != "V29_TIME_SCOPE_V1" or data.get("as_of") != "2026-11-09":
        errors.append("Schema or immutable as-of changed")
    if not isinstance(data.get("purpose"), str) or not data["purpose"].strip():
        errors.append("Missing description")
    controls = data.get("controls")
    if not isinstance(controls, dict) or controls != CONTROL_FIELDS:
        errors.append("Evidence safety controls changed")
    records = data.get("claims")
    if not isinstance(records, list):
        records = []
        errors.append("Claims must be an array")
    found = set()
    for i, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append("Claim not object: " + str(i))
            continue
        name = row.get("id")
        if set(row) != CLAIM_FIELDS:
            errors.append("Unknown/missing claim fields: " + str(name))
        if not isinstance(name, str) or name not in CLAIMS:
            errors.append("Unregistered claim: " + str(name))
            continue
        if name in found:
            errors.append("Duplicate claim: " + name)
        found.add(name)
        expected = CLAIMS[name]
        if tuple(row.get(k) for k in PINNED_FIELDS) != expected:
            errors.append("Pinned claim changed: " + name)
        if not isinstance(row.get("source_qualification"), str) or not row["source_qualification"].strip():
            errors.append("Missing qualification: " + name)
        for field in ("source_document_bytes_authenticated",
                      "physical_commissioning_verified",
                      "actual_paid_bering_cargo_verified"):
            if row.get(field) is not False:
                errors.append("Unsupported verification promotion: " + name + "/" + field)
    if found != set(CLAIMS) or len(records) != len(CLAIMS):
        errors.append("Claim set or count changed")
    valid = not errors
    return {
        "status": "RESEARCH_CONTEXT_ONLY" if valid else "INVALID",
        "as_of": "2026-11-09",
        "reviewed_claim_rows": len(records) if valid else None,
        "design_may_2026_teu_per_year": "30000" if valid else None,
        "design_oct_2026_teu_per_year": "150000" if valid else None,
        "same_revision_proven": False,
        "design_versions_sum_teu_per_year": None,
        "planned_2030_commission_year": "2030" if valid else None,
        "verified_commission_year": None,
        "verified_in_service_capacity_teu_per_year": None,
        "operator_nov_2026_available_capacity_document_listed": True if valid else None,
        "operator_nov_2026_actual_containers": None,
        "new_paid_bering_40ft": None,
        "group_incremental_cm_rub": None,
        "bering_npv_rub": None,
        "bankable_revenue_approved": False,
        "investment_approved": False,
        "P1": "HOLD", "P2": "HOLD", "P3": "HOLD",
        "errors": errors
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path,
                        default=Path("data/public/V29_COMPETITOR_TIMELINE_CLAIMS.json"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.register.read_text(encoding="utf-8"))
        report = evaluate(data)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        report = evaluate({})
        report["errors"].append("Source load failed: " + type(error).__name__)
    value = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(value, encoding="utf-8")
    print(value, end="")
    return 2 if report["status"] == "INVALID" else 0

if __name__ == "__main__":
    raise SystemExit(main())
