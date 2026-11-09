#!/usr/bin/env python3
"""Bering V30 evidence admission: verify published-source byte claims, not bankability.

A Git-stored SHA receipt is NOT independent verification of the PDF bytes.
Passing --pdf-root enables actual SHA-256 recomputation on the local public copies;
those original binaries are intentionally not committed to this research repo.
Commercial and investment admission remain HOLD regardless of source retrieval.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

INPUTS = {
    "owner_index": "data/public/V28_MLC_PRIMARY_PROJECT_FILE_MANIFEST.json",
    "byte_receipt": "data/public/V30_PUBLIC_PDF_BYTE_AUDIT_20261109.json",
    "page_review": "data/public/V30_PDF_SOURCE_FINDINGS_20261109.json",
    "commercial_intake": "data/pilots/V30_EXTERNAL_SOURCE_INTAKE_20261109.json",
    "ci_diagnostic": "quality/V30_CI_PRE_RUNNER_DIAGNOSTIC_20261109.json",
    "od_matrix": "data/od/V27_REQUIRED_COVERAGE_96.csv",
}
GROUPS = {"P1", "P2", "P3", "GROUP_EXISTING"}
MONTHS = {
    f"{year:04d}-{month:02d}"
    for year in (2024, 2025, 2026)
    for month in range(1, 13)
    if (year, month) >= (2024, 10) and (year, month) <= (2026, 9)
}
AUDIT_DATE = "2026-11-09"
EXPECTED_MATCHES = 4
EXPECTED_SELECTED = 10

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def read_in_repo(repo, rel):
    path = repo / rel
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(repo):
        raise ValueError("Missing or unsafe source file: " + rel)
    return path.read_text(encoding="utf-8")

def evaluate(repo, pdf_root=None):
    repo = Path(repo).resolve()
    errors = []
    try:
        sources = {k: read_in_repo(repo, p) for k, p in INPUTS.items()}
        owner = json.loads(sources["owner_index"])
        audit = json.loads(sources["byte_receipt"])
        review = json.loads(sources["page_review"])
        intake = json.loads(sources["commercial_intake"])
        ci = json.loads(sources["ci_diagnostic"])
        od = list(csv.DictReader(sources["od_matrix"].splitlines()))
    except (OSError, ValueError, UnicodeError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "INVALID", "errors": ["Cannot load evidence: " + type(exc).__name__],
                "bankable_revenue_approved": False, "investment_approved": False, "P1":"HOLD","P2":"HOLD","P3":"HOLD"}

    def require(ok, reason):
        if not ok:
            errors.append(reason)

    originals = owner.get("documents", []) if isinstance(owner, dict) else []
    by_path = {}
    for record in originals:
        if not isinstance(record, dict):
            errors.append("Malformed owner manifest row")
            continue
        name = record.get("path")
        if name in by_path:
            errors.append("Duplicate owner document path")
        by_path[name] = record
    require(len(by_path) == 52, "Owner document manifest must remain 52 unique rows")
    require(owner.get("document_contents_verified") == 0 and
            owner.get("positive_expertise_2026_matches_uploaded_2025_revisions") is False,
            "Earlier unverified original-review status was rewritten")
    require(audit.get("schema") == "V30_PUBLIC_DOCUMENT_BYTE_CHECK_V1" and
            audit.get("as_of") == AUDIT_DATE and
            audit.get("source_public_link") == "https://disk.yandex.ru/d/VBtKSnvIO1rolQ",
            "Wrong public byte receipt identity")
    require(audit.get("approved_2026_design_revision_verified") is False and
            audit.get("investment_approved") is False, "Public download was promoted to approval")

    rows = audit.get("files", [])
    if not isinstance(rows, list):
        errors.append("No byte receipt file rows")
        rows = []
    selected = set()
    receipt_matches = 0
    local_verified = None if pdf_root is None else 0
    local_not_present = None if pdf_root is None else 0
    if pdf_root is not None:
        pdf_root = Path(pdf_root).resolve()
        require(pdf_root.is_dir(), "PDF root is missing")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append("Malformed byte receipt row: " + str(index))
            continue
        source_path = row.get("remote_file_path")
        if source_path in selected:
            errors.append("Duplicate checked public PDF")
            continue
        selected.add(source_path)
        original = by_path.get(source_path)
        if original is None:
            errors.append("Unknown owner source path")
            continue
        name = original["path"].rsplit("/", 1)[-1]
        expected = original.get("sha256_from_public_api")
        size = original.get("bytes")
        require(isinstance(expected, str) and len(expected) == 64, "Owner digest absent")
        require(row.get("file_basename") == name and
                row.get("expected_bytes") == size and
                row.get("expected_yandex_sha256") == expected,
                "Byte receipt changed original identity / digest / size")
        marked = row.get("downloaded") is True
        if marked:
            ok = (row.get("download_http_status") == 200
                  and row.get("error") is None
                  and row.get("sha256_matches_owner") is True
                  and row.get("byte_length_matches_owner") is True
                  and row.get("byte_sha256") == expected
                  and row.get("actual_bytes") == size)
            require(ok, "Claimed byte verification is inconsistent: " + name)
            if ok:
                receipt_matches += 1
        else:
            require(row.get("downloaded") is False
                    and row.get("byte_sha256") is None
                    and row.get("actual_bytes") is None
                    and row.get("sha256_matches_owner") is False
                    and row.get("byte_length_matches_owner") is False
                    and isinstance(row.get("error"), str)
                    and "HTTP Error 429" in row["error"],
                    "Failed download was concealed or mislabeled: " + name)
        if pdf_root is not None:
            local = pdf_root / name
            if local.is_symlink():
                errors.append("Unsafe source symlink: " + name)
            elif local.is_file():
                if not local.resolve().is_relative_to(pdf_root):
                    errors.append("Out-of-directory source: " + name)
                elif digest(local) != expected or local.stat().st_size != size:
                    errors.append("Local source bytes do not match owner SHA/size: " + name)
                elif not marked:
                    errors.append("Local file exists despite missing recorded download: " + name)
                else:
                    local_verified += 1
            else:
                local_not_present += 1

    require(len(rows) == EXPECTED_SELECTED and len(selected) == EXPECTED_SELECTED and
            audit.get("attempted") == EXPECTED_SELECTED,
            "V30 selected source count/uniqueness changed")
    require(receipt_matches == EXPECTED_MATCHES and
            audit.get("sha_match_count") == EXPECTED_MATCHES and
            audit.get("size_match_count") == EXPECTED_MATCHES,
            "Selected public byte receipt count changed")

    findings = review.get("findings", [])
    require(review.get("schema") == "V30_PRIMARY_PDF_REVIEW_V1" and
            review.get("as_of") == AUDIT_DATE and
            review.get("official_2026_positive_expertise_revisions_match_verified") is False and
            review.get("capacity_30000_150000_official_change_log_verified") is False and
            review.get("bankable_revenue_approved") is False and
            review.get("investment_approved") is False,
            "Source review improperly promotes expertise/finance")
    require(isinstance(findings, list) and len(findings) == 1,
            "Expected one scoped geographical text finding")
    if isinstance(findings, list) and len(findings) == 1 and isinstance(findings[0], dict):
        finding = findings[0]
        require(finding.get("file") == "/Том 10.1 П-25-2025-00-ТБЭ-10.1.pdf" and
                finding.get("sha256") == by_path.get(finding.get("file"), {}).get("sha256_from_public_api") and
                finding.get("pdf_pages_one_based") == [12,13] and
                finding.get("verified_in_observed_2025_public_copy") is True and
                finding.get("verified_in_approved_oct2026_revision") is False and
                finding.get("investment_approved") is False,
                "Geographical discrepancy provenance was altered")

    require(intake.get("schema") == "V30_EXTERNAL_PRIMARY_SOURCE_REQUESTS_V1" and
            intake.get("as_of") == AUDIT_DATE and intake.get("months") == 24 and
            set(intake.get("group_or_pilot_ids", [])) == GROUPS and
            intake.get("period_first") == "2024-10" and
            intake.get("period_last") == "2026-09" and
            intake.get("expected_month_slots") == 96 and
            intake.get("authenticated_month_slots") == 0,
            "OD coverage assertions changed")
    for metric in ("requests_submitted","raw_contracts_received","original_waybills_received",
                   "verified_receipt_events","paid_invoices_received","verified_bank_settlements"):
        require(intake.get(metric) == 0 and not isinstance(intake.get(metric), bool),
                "Unverified commercial evidence declared: " + metric)
    for metric in ("primary_actual_40ft_shipment_count","new_group_incremental_contribution_margin_rub","bering_npv_rub"):
        require(intake.get(metric) is None, "Unknown financial / cargo quantity must remain null: " + metric)
    for k in ("requests_sent","contact_details_for_pilots_verified","client_permission_to_use_raw_records",
              "raw_data_in_repository","investment_approved"):
        require(intake.get(k) is False, "Unverified intake flag promoted: " + k)
    require([intake.get("P1"),intake.get("P2"),intake.get("P3")] == ["HOLD"] * 3,
            "Pilot source intake incorrectly released")

    slots = set()
    for row in od:
        key = (row.get("pilot_id"), row.get("month"))
        if key in slots:
            errors.append("Duplicate group-month slot")
        slots.add(key)
        require(row.get("current_status") == "MISSING_NOT_ZERO" and
                not row.get("source_attested") and not row.get("physical_containers_40ft") and
                not row.get("source_file_sha256") and not row.get("source_row_locator"),
                "Unauthenticated OD row promoted to actual source")
    require(len(od) == 96 and slots == {(g,m) for g in GROUPS for m in MONTHS},
            "24-month four-group OD coverage changed")

    jobs = ci.get("github_hosted_runner_job_runs", [])
    require(ci.get("schema") == "V30_CI_PRE_RUNNER_DIAGNOSTICS_V1" and
            ci.get("as_of") == AUDIT_DATE and ci.get("actions_enabled") is True and
            ci.get("actions_allowed_actions") == "all" and
            ci.get("workflow_default_permissions") == "read" and
            ci.get("github_hosted_runner_allocation_cause") == "UNKNOWN" and
            ci.get("github_hosted_runner_billing_status_verified") is False and
            ci.get("github_hosted_ci_green") is False and
            ci.get("external_independent_acceptance_completed") is False and
            ci.get("investment_approved") is False,
            "CI scope or gate modified")
    require(isinstance(jobs, list) and len(jobs) == 3 and
            len({j.get("run") for j in jobs if isinstance(j, dict)}) == 3 and
            all(j.get("status") == "completed" and j.get("conclusion") == "failure"
                and j.get("runner_id") == 0 and j.get("steps_executed") == 0
                for j in jobs if isinstance(j, dict)),
            "Pre-runner GitHub job results were incorrectly promoted")

    return {
        "status": "INVALID" if errors else "HOLD",
        "source_scope_status": ("INVALID" if errors else
            "PARTIAL_LOCAL_PDF_BYTES_VERIFIED" if pdf_root is not None and local_verified else
            "RECEIPT_ONLY_BYTES_NOT_RECOMPUTED"),
        "public_source_documents_in_owner_manifest": len(by_path),
        "selected_public_pdf_downloads": len(rows),
        "claimed_digest_matches_in_versioned_receipt": receipt_matches,
        "source_bytes_recomputed_at_runtime": local_verified,
        "source_files_not_locally_present": local_not_present,
        "official_2026_expertise_approved_revision_matched": False,
        "source_geographic_discrepancy_in_2025_public_copy": True,
        "source_geographic_discrepancy_resolved_in_2026_revision": False,
        "od_required_group_months": len(od),
        "od_authenticated_group_months": 0,
        "requests_submitted": 0,
        "real_new_paid_40ft": None,
        "group_incremental_cm_rub": None,
        "bering_npv_rub": None,
        "github_actions_green": False,
        "independent_external_acceptance_complete": False,
        "P1":"HOLD","P2":"HOLD","P3":"HOLD",
        "bankable_revenue_approved": False,
        "investment_approved": False,
        "errors": errors,
        "limitations": "Byte-level match against owner-public metadata is not approved-design authenticity. Tests do not create customer records, paid cargo or independent certification."
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--pdf-root", type=Path,
                        help="Local temporary public PDF directory. Never commit raw PDFs.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = evaluate(args.repo, args.pdf_root)
    result = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(result, encoding="utf-8")
    print(result, end="")
    return 2 if report["status"] == "INVALID" else 0

if __name__ == "__main__":
    sys.exit(main())
