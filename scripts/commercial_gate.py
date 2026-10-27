#!/usr/bin/env python3
"""Evidence-first Magadan commercial gate. No automatic investment approval."""
from __future__ import annotations
import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

DOCUMENT_FIELDS = (
    "signed_contract", "firm_quote", "waybill", "actual_delivery",
    "invoice", "payment", "baseline_24m", "additionality",
    "capacity", "legal_review",
)
EXPECTED_COMPONENTS = (
    "pickup", "origin_handling", "freight", "storage", "destination_handling",
    "last_mile", "insurance", "equipment",
)
IDENTIFIER = re.compile(r"^EV-[A-Z0-9][A-Z0-9_-]{5,}$")
PLACEHOLDERS = {"", "0", "N/A", "NA", "NONE", "UNKNOWN", "PENDING",
                "NOT VERIFIED", "NOT RECEIVED", "НЕ ПОЛУЧЕНО", "НЕ ПРОВЕРЕНО"}


def valid_evidence(value):
    return isinstance(value, str) and value.strip().upper() not in PLACEHOLDERS and bool(IDENTIFIER.fullmatch(value.strip()))


def verified_record(identifier, records):
    if not valid_evidence(identifier):
        return False
    row = records.get(identifier)
    if not isinstance(row, dict):
        return False
    digest = row.get("sha256")
    return (row.get("status") == "VERIFIED"
            and isinstance(digest, str)
            and bool(re.fullmatch(r"[0-9a-f]{64}", digest))
            and bool(str(row.get("reviewed_by") or "").strip())
            and bool(str(row.get("reviewed_on") or "").strip()))


def number(value, label, errors, *, positive=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        errors.append(f"{label}: boolean is not a number")
        return None
    try:
        n = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors.append(f"{label}: not numeric")
        return None
    if not n.is_finite() or n < 0 or (positive and n == 0):
        errors.append(f"{label}: non-finite or invalid sign")
        return None
    return n


def evaluate(case):
    errors, missing = [], []
    code = case.get("pilot_id")
    if code not in {"P1", "P2", "P3"}:
        errors.append("pilot_id: must be P1/P2/P3")
    unit = case.get("unit")
    if unit != "40ft_container":
        errors.append("unit: only 40ft_container supported; do not mix TEU or tonnes")
    for f in ("origin", "destination", "cargo_class", "route_id"):
        if not isinstance(case.get(f), str) or not case[f].strip():
            errors.append(f"{f}: required")
    docs = case.get("documents") or {}
    records = case.get("evidence_records") or {}
    for key in DOCUMENT_FIELDS:
        if not verified_record(docs.get(key), records):
            missing.append(f"document:{key}")
    supplied_doc_ids = [docs[k] for k in DOCUMENT_FIELDS if valid_evidence(docs.get(k))]
    if len(set(supplied_doc_ids)) != len(supplied_doc_ids):
        errors.append("documents: distinct categories must not reuse one evidence ID")

    components = case.get("d2d_components") or []
    seen, cost, complete_cost = set(), Decimal(0), True
    if case.get("cost_currency") != "RUB" or case.get("cost_tax_basis") != "EX_VAT":
        errors.append("d2d: this version requires comparable RUB EX_VAT costs")
        complete_cost = False
    valid_names = EXPECTED_COMPONENTS + (("customs",) if code == "P3" else ())
    for c in components:
        name = c.get("name")
        if name in seen:
            errors.append(f"d2d: duplicate component {name}")
        seen.add(name)
        if name not in valid_names:
            errors.append(f"d2d: unknown component {name}")
        if not verified_record(c.get("evidence_id"), records):
            missing.append(f"d2d:{name}:evidence")
            complete_cost = False
        included = c.get("included_in_freight")
        amount = number(c.get("amount_rub"), f"d2d:{name}:amount_rub", errors)
        if included is True:
            if name == "freight":
                errors.append("d2d: freight cannot be included in itself")
            if amount is not None and amount != 0:
                errors.append(f"d2d:{name}: positive amount duplicated in freight")
        elif included is False:
            if amount is None:
                missing.append(f"d2d:{name}:amount_rub")
                complete_cost = False
            else:
                cost += amount
        else:
            missing.append(f"d2d:{name}:included_in_freight")
            complete_cost = False
    for name in valid_names:
        if name not in seen:
            missing.append(f"d2d:{name}:component")
            complete_cost = False
    d2d_cost = cost if complete_cost and not errors else None

    volumes = case.get("volumes") or {}
    contract = number(volumes.get("contracted"), "volumes:contracted", errors, positive=True)
    diverted = number(volumes.get("diverted"), "volumes:diverted", errors)
    duplicated = number(volumes.get("duplicated"), "volumes:duplicated", errors)
    if any(v is None for v in (contract, diverted, duplicated)):
        missing.append("volumes:complete_triplet")
        net_new = None
    elif diverted + duplicated > contract:
        errors.append("volumes:diverted+duplicated exceeds contracted")
        net_new = None
    else:
        net_new = contract - diverted - duplicated
    m = case.get("margin") or {}
    new_cm = number(m.get("new_unit_contribution_rub"), "margin:new_unit", errors)
    old_cm = number(m.get("displaced_old_unit_contribution_rub"), "margin:old_unit", errors)
    fixed = number(m.get("incremental_fixed_opex_rub"), "margin:fixed", errors)
    risk = number(m.get("incremental_risk_cost_rub"), "margin:risk", errors)
    if any(v is None for v in (new_cm, old_cm, fixed, risk)) or net_new is None:
        missing.append("margin:complete_inputs")
        incremental_cm = None
    else:
        incremental_cm = net_new * new_cm + diverted * (new_cm - old_cm) - fixed - risk

    valid = not errors
    complete = valid and not missing and d2d_cost is not None and incremental_cm is not None
    gate = "REVIEW" if complete and incremental_cm > 0 else "HOLD"
    validated_volume_evidence = all(verified_record(docs.get(k), records)
                                    for k in ("signed_contract", "baseline_24m", "additionality"))
    return {"pilot_id": code, "gate": gate,
            "net_new_40ft_containers": float(net_new) if valid and validated_volume_evidence and net_new is not None else None,
            "d2d_rub_ex_vat": float(d2d_cost) if valid and d2d_cost is not None else None,
            "incremental_group_cm_rub": float(incremental_cm) if complete else None,
            "errors": errors, "missing": sorted(set(missing)),
            "bankable_revenue_approved": False,
            "manual_review_required": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    a = parser.parse_args()
    results = [evaluate(json.loads(p.read_text(encoding="utf-8"))) for p in a.inputs]
    body = json.dumps({"evaluated": len(results), "results": results}, ensure_ascii=False, indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(body+"\n", encoding="utf-8")
    print(body)
    return 1 if any(r["errors"] for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
