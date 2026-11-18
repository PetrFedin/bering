"""Fail-closed research tests; no production or external-origin file is assumed."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
from r21_source_integrity_and_freight_scope import evaluate, check_source_bytes

SOURCE = ROOT / "data/public/R21_OFFICIAL_SOURCE_INTAKE_20261118.json"
BASE = json.loads(SOURCE.read_text(encoding="utf-8"))


class R21ProofBoundaryTests(unittest.TestCase):
    def test_01_baseline_is_research_only(self):
        a=evaluate(BASE)
        self.assertEqual(a["status"],"RESEARCH_CONTEXT_ONLY",a["errors"])
        self.assertFalse(a["investment_approved"])
        self.assertIsNone(a["bering_npv_rub"])
        self.assertFalse(a["originals_rehashed_at_this_runtime"])

    def reject(self,change):
        x=copy.deepcopy(BASE);change(x)
        result=evaluate(x)
        self.assertEqual(result["status"],"INVALID",result["errors"])
        self.assertFalse(result["investment_approved"])
        self.assertIsNone(result["paid_incremental_40ft"])

    def test_02_bad_asof(self):self.reject(lambda x:x.__setitem__("as_of","2026-11-17"))
    def test_03_bad_schema(self):self.reject(lambda x:x.__setitem__("schema","V22"))
    def test_04_bad_source_scope(self):self.reject(lambda x:x.__setitem__("source_scope","ALL_MAGADAN_PORT"))
    def test_05_missing_doc(self):self.reject(lambda x:x["files"].pop())
    def test_06_duplicate_doc(self):self.reject(lambda x:x["files"].append(copy.deepcopy(x["files"][0])))
    def test_07_unknown_doc(self):self.reject(lambda x:x["files"][0].__setitem__("id","FICTITIOUS"))
    def test_08_changed_hash(self):self.reject(lambda x:x["files"][0].__setitem__("sha256","0"*64))
    def test_09_wrong_period(self):self.reject(lambda x:x["files"][2].__setitem__("period","2026-9M"))
    def test_10_false_prior_hash_match(self):self.reject(lambda x:x["files"][2].__setitem__("recorded_hash_matches_prior_repo_csv",True))
    def test_11_false_cell_read(self):self.reject(lambda x:x["files"][0].__setitem__("cell_values_authenticated",True))
    def test_12_hidden_filepass(self):self.reject(lambda x:x["files"][0].__setitem__("cell_validation_status","OPENED"))
    def test_13_wrong_file_url(self):self.reject(lambda x:x["files"][1].__setitem__("url",x["files"][0]["url"]))
    def test_14_wrong_file_size(self):self.reject(lambda x:x["files"][3].__setitem__("bytes",40054))
    def test_15_wrong_format(self):self.reject(lambda x:x["files"][3].__setitem__("format","OLE_BIFF_XLS"))
    def test_16_false_port_capacity(self):self.reject(lambda x:x["controls"].__setitem__("usable_2026_operational_capacity_verified",True))
    def test_17_false_scope_reconciliation(self):self.reject(lambda x:x["controls"].__setitem__("whole_port_2024_2025_scope_reconciled",True))
    def test_18_fake_paid_freight(self):self.reject(lambda x:x["controls"].__setitem__("paid_incremental_shipment_40ft",300))
    def test_19_fake_npv(self):self.reject(lambda x:x["controls"].__setitem__("bering_npv_rub",1))
    def test_20_fake_revenue_approval(self):self.reject(lambda x:x["controls"].__setitem__("bankable_revenue_approved",True))
    def test_21_fake_investment(self):self.reject(lambda x:x["controls"].__setitem__("investment_approved",True))
    def test_22_fake_rate(self):self.reject(lambda x:x["tariff_scope"].__setitem__("fesco_fml_rub_per_40ft_verified",170000))
    def test_23_fake_comparability(self):self.reject(lambda x:x["tariff_scope"].__setitem__("like_for_like_carrier_quote_verified",True))
    def test_24_fake_terminal_tariff_included(self):self.reject(lambda x:x["tariff_scope"].__setitem__("fit_terminal_charges_verified_in_fml_base",True))
    def test_25_wrong_sasco_rate(self):self.reject(lambda x:x["tariff_scope"].__setitem__("sasco_dry_40_coc_rub_ex_vat_previous_register",210671))
    def test_26_wrong_fesco_index_date(self):self.reject(lambda x:x["tariff_scope"].__setitem__("fesco_fml_public_index_date","2026-05-21"))
    def test_27_malformed_list(self):self.reject(lambda x:x.__setitem__("files",{"oops":1}))

    def test_39_unhashable_source_id_is_rejected_without_exception(self):
        self.reject(lambda x: x["files"][0].__setitem__("id", []))

    def test_28_source_order_irrelevant(self):
        x=copy.deepcopy(BASE);x["files"].reverse()
        self.assertEqual(evaluate(x)["status"],"RESEARCH_CONTEXT_ONLY")

    def test_29_tax_arithmetic_no_comparison(self):
        s=evaluate(BASE)["tax_stress_not_an_actual_quote"]
        self.assertEqual(s["naive_kmp_minus_sasco_rub"],"29097")
        self.assertEqual(s["hypothetical_sasco_40dc_gross_rub_if_22pct_applies"],"257017.40")
        self.assertEqual(s["hypothetical_sasco_gross_minus_kmp_rub"],"17250.40")
        self.assertFalse(s["comparison_admissible"])

    def test_30_reef_arithmetic_only(self):
        s=evaluate(BASE)["tax_stress_not_an_actual_quote"]
        self.assertEqual(s["hypothetical_sasco_40rf_gross_rub_if_22pct_applies"],"283247.40")
        self.assertIsNone(evaluate(BASE)["fesco_fml_rate_rub"])

    def test_31_matching_local_bytes_not_authenticity(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"sample.xls"; data=b"synthetic-file";p.write_bytes(data)
            self.assertEqual(check_source_bytes(p,hashlib.sha256(data).hexdigest(),len(data)),"LOCAL_BYTES_MATCH_ONLY")
            self.assertFalse(evaluate(BASE)["original_cells_authenticated"])

    def test_32_byte_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"f";p.write_bytes(b"bad")
            self.assertEqual(check_source_bytes(p,hashlib.sha256(b"good").hexdigest(),3),"HASH_MISMATCH")

    def test_33_byte_size_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"f";p.write_bytes(b"bad")
            self.assertEqual(check_source_bytes(p,hashlib.sha256(b"bad").hexdigest(),4),"SIZE_MISMATCH")

    def test_34_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(check_source_bytes(Path(td)/"missing", "a"*64),"MISSING_OR_UNSAFE")

    def test_35_symlink_is_unsafe(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"file";p.write_text("x");symlink=Path(td)/"link";symlink.symlink_to(p)
            self.assertEqual(check_source_bytes(symlink,hashlib.sha256(b"x").hexdigest()),"MISSING_OR_UNSAFE")

    def test_36_bad_private_root(self):
        with tempfile.TemporaryDirectory() as td:
            x=evaluate(BASE,Path(td)/"missing")
            self.assertEqual(x["status"],"INVALID")

    def test_37_empty_private_root_never_promotes(self):
        with tempfile.TemporaryDirectory() as td:
            x=evaluate(BASE,Path(td))
            self.assertEqual(x["status"],"RESEARCH_CONTEXT_ONLY")
            self.assertTrue(all(v=="MISSING_OR_UNSAFE" for v in x["local_byte_results"].values()))
            self.assertFalse(x["originals_rehashed_at_this_runtime"])
            self.assertFalse(x["investment_approved"])

    def test_38_corrupt_json_cli_exits_two(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/"bad.json";bad.write_text("{bad",encoding="utf-8")
            proc=subprocess.run([sys.executable,str(ROOT/"scripts/r21_source_integrity_and_freight_scope.py"),"--manifest",str(bad)],capture_output=True,text=True,cwd=ROOT)
            self.assertEqual(proc.returncode,2)
            self.assertFalse(json.loads(proc.stdout)["investment_approved"])

if __name__=="__main__":unittest.main()
