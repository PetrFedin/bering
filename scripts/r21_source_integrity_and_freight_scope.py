#!/usr/bin/env python3
"""R21: pinned source-byte provenance and non-comparable tariff scope.

The snapshot is a historical external-source receipt, not a signature or a
re-read of XLS cells. Even a byte match cannot establish cargo revenue.
"""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PINS = {
    "MMTP_MP1_FY2024": ("2024-FY", "MP10014724_official_2024.xls", "304ffdf9c41c3e2803c49d351c61bb8ef891c36a068e3072c5dc119c8eb985e9", None, "FILEPASS_BLOCKED", True),
    "MMTP_MP1_FY2025": ("2025-FY", "MP10014725_official_2025.xls", "a8974d03d578276fde70e54f56036170f71d4256a2f12fcc3c2a0c15c7c77121", 282112, "NOT_REREAD", True),
    "MMTP_MP1_H1_2026": ("2026-H1", "MP10014726_official_2026h1.xls", "e96a32f7cd6af6364c4606a35d3bc69d25124139ab1cc97d39ee950efb0a307d", 244224, "NOT_REREAD", None),
    "MMTP_INFRASTRUCTURE_REGISTER_2026": ("2026-SNAPSHOT_UNDATED", "port_register_2026.xlsx", "fcc4e4e80b0924d58b4cab9a6f1f9116b970b9399750bf1bd07efb0fb527e22e", 40055, "NOT_REREAD", None),
}
SOURCE_URLS = {
    "MMTP_MP1_FY2024": "https://www.magadanport.ru/wp-content/uploads/2025/01/MP10014724.xls",
    "MMTP_MP1_FY2025": "https://www.magadanport.ru/wp-content/uploads/2026/01/MP10014725.xls",
    "MMTP_MP1_H1_2026": "https://www.magadanport.ru/wp-content/uploads/2026/07/MP10014726.xls",
    "MMTP_INFRASTRUCTURE_REGISTER_2026": "https://www.magadanport.ru/wp-content/uploads/2026/05/%D0%A1%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B8%D1%8F-%D0%B8%D0%B7-%D1%80%D0%B5%D0%B5%D1%81%D1%82%D1%80%D0%B0-1-1.xlsx"
}
RATES = {"sasco_dry_40_coc_rub_ex_vat_previous_register": 210670,
         "sasco_reefer_40_soc_rub_ex_vat_previous_register": 232170,
         "kmp_dry_40_rub_including_tax_previous_register": 239767,
         "kmp_reefer_40_rub_including_tax_previous_register": 315000}


def check_source_bytes(file_path, sha, expected_size=None):
    """Integrity of received bytes only, never issuer authenticity."""
    p = Path(file_path)
    if not p.is_file() or p.is_symlink():
        return "MISSING_OR_UNSAFE"
    try:
        raw = p.read_bytes()
    except (OSError, PermissionError):
        return "UNREADABLE"
    if expected_size is not None and len(raw) != expected_size:
        return "SIZE_MISMATCH"
    if hashlib.sha256(raw).hexdigest() != sha:
        return "HASH_MISMATCH"
    return "LOCAL_BYTES_MATCH_ONLY"


def evaluate(packet, private_root=None):
    errors = []
    if not isinstance(packet, dict):
        packet = {}; errors.append("NOT_AN_OBJECT")
    if packet.get("schema") != "BERING_R21_PRIMARY_FILE_METADATA_V1":
        errors.append("SCHEMA_VERSION")
    if packet.get("as_of") != "2026-11-18":
        errors.append("SNAPSHOT_DATE")
    if packet.get("source_scope") != "PAO_MMTP_PUBLIC_OPERATOR_FILES_NOT_WHOLE_PORT":
        errors.append("SOURCE_PERIMETER")
    sources = packet.get("files")
    if not isinstance(sources, list):
        sources = []; errors.append("SOURCES_NOT_LIST")
    seen = set()
    for entry in sources:
        if not isinstance(entry, dict):
            errors.append("SOURCE_NOT_OBJECT"); continue
        key = entry.get("id")
        if not isinstance(key, str) or key not in PINS:
            errors.append("UNKNOWN_SOURCE"); continue
        if key in seen:
            errors.append("DUPLICATE_SOURCE")
        seen.add(key)
        period, name, sha, byte_count, read_status, prior_match = PINS[key]
        if any((entry.get("period") != period, entry.get("file_name") != name,
                entry.get("sha256") != sha, entry.get("bytes") != byte_count,
                entry.get("cell_validation_status") != read_status,
                entry.get("recorded_hash_matches_prior_repo_csv") != prior_match,
                entry.get("cell_values_authenticated") is not False)):
            errors.append("PROMOTED_OR_CHANGED_PRIMARY_SOURCE_" + key)
        fmt = "XLSX_ZIP" if name.endswith(".xlsx") else "OLE_BIFF_XLS"
        if entry.get("format") != fmt or entry.get("url") != SOURCE_URLS[key]:
            errors.append("SOURCE_FORMAT_OR_URL_" + key)
    if len(sources) != len(PINS) or set(PINS) != seen:
        errors.append("SOURCE_SET_MISMATCH")
    rates = packet.get("tariff_scope")
    if not isinstance(rates, dict):
        rates={};errors.append("TARIFF_SCOPE_NOT_OBJECT")
    for key, value in RATES.items():
        if type(rates.get(key)) is not int or rates[key] != value:
            errors.append("RATE_PIN_MISMATCH_"+key)
    for k in ("fesco_fml_rub_per_40ft_verified",):
        if rates.get(k) is not None:
            errors.append("UNVERIFIED_FESCO_RATE_PROMOTED")
    if rates.get("fesco_fml_public_index_date") != "2026-11-17" or rates.get("fesco_fit_magadan_tariff_index_date") != "2026-11-05":
        errors.append("FESCO_INDEX_DATES")
    for k in ("tax_rate_22pct_applicable_to_named_quotes_verified", "like_for_like_carrier_quote_verified", "fit_terminal_charges_verified_in_fml_base"):
        if rates.get(k) is not False:
            errors.append("UNVERIFIED_QUOTE_PROMOTED_"+k)
    controls = packet.get("controls")
    if not isinstance(controls, dict):
        controls={};errors.append("CONTROLS_NOT_OBJECT")
    for k in ("original_cells_authenticated", "whole_port_2024_2025_scope_reconciled", "usable_2026_operational_capacity_verified", "signed_competitor_mlc_project_verified", "bankable_revenue_approved", "investment_approved"):
        if controls.get(k) is not False:
            errors.append("UNVERIFIED_DECISION_PROMOTED_"+k)
    for k in ("paid_incremental_shipment_40ft","incremental_group_cm_rub", "bering_npv_rub"):
        if controls.get(k) is not None:
            errors.append("UNKNOWN_AMOUNT_PROMOTED_"+k)
    if controls.get("p1_p2_p3_hold") is not True:
        errors.append("PILOT_HOLD_REMOVED")
    # Additional checks are advisory: no promotion even if file bytes match.
    local = {}
    if private_root is not None:
        root = Path(private_root)
        if not root.is_dir() or root.is_symlink():
            errors.append("PRIVATE_ROOT_UNSAFE")
        else:
            for k, (_, name, sha, byte_count, _, _) in PINS.items():
                local[k] = check_source_bytes(root/name, sha, byte_count)
    dry_sasco = Decimal(RATES["sasco_dry_40_coc_rub_ex_vat_previous_register"])
    dry_kmp = Decimal(RATES["kmp_dry_40_rub_including_tax_previous_register"])
    rf_sasco = Decimal(RATES["sasco_reefer_40_soc_rub_ex_vat_previous_register"])
    rf_kmp = Decimal(RATES["kmp_reefer_40_rub_including_tax_previous_register"])
    sample_vat=Decimal("0.22")
    return {
        "status": "RESEARCH_CONTEXT_ONLY" if not errors else "INVALID",
        "source_access": "FOUR_FILES_RECEIVED_HASHED_ON_MAC_NOT_CELLS_AUTHENTICATED" if not errors else "INVALID",
        "original_cells_authenticated": False,
        "operator_all_port_scope_reconciled": False,
        "originals_rehashed_at_this_runtime": bool(private_root is not None and local) and all(x=="LOCAL_BYTES_MATCH_ONLY" for x in local.values()),
        "local_byte_results": local,
        "tax_stress_not_an_actual_quote": {
            "assumed_standard_vat_rate_pct": "22",
            "sasco_40dc_nominal_ex_vat_rub": str(dry_sasco),
            "kmp_40dc_recorded_tax_inclusive_rub": str(dry_kmp),
            "naive_kmp_minus_sasco_rub": str(dry_kmp-dry_sasco),
            "hypothetical_sasco_40dc_gross_rub_if_22pct_applies": str((dry_sasco*(1+sample_vat)).quantize(Decimal("0.01"))),
            "hypothetical_sasco_gross_minus_kmp_rub": str(((dry_sasco*(1+sample_vat))-dry_kmp).quantize(Decimal("0.01"))),
            "hypothetical_sasco_40rf_gross_rub_if_22pct_applies": str((rf_sasco*(1+sample_vat)).quantize(Decimal("0.01"))),
            "kmp_40rf_recorded_tax_inclusive_rub": str(rf_kmp),
            "comparison_admissible": False,
            "reason": "Unresolved COC/SOC, tax rates, included handling, validity and FESCO FIT terminal scope"
        },
        "fesco_fml_rate_rub": None,
        "available_port_capacity_2026": None,
        "paid_incremental_40ft": None,
        "incremental_group_cm_rub": None,
        "bering_npv_rub": None,
        "pilot_gates": {"P1":"HOLD","P2":"HOLD","P3":"HOLD"},
        "investment_approved": False,
        "errors": errors
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,default=BASE/"data/public/R21_OFFICIAL_SOURCE_INTAKE_20261118.json")
    p.add_argument("--private-root",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    try:
        manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError):
        manifest={}
    result=evaluate(manifest, private_root=a.private_root)
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.out:
        a.out.write_text(output,encoding="utf-8")
    print(output,end="")
    return 0 if result["status"]=="RESEARCH_CONTEXT_ONLY" else 2

if __name__=="__main__":
    raise SystemExit(main())
