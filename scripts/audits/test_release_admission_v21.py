import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from release_admission_v21 import execute

class V21Admission(unittest.TestCase):
    def test_empty_checkout_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=execute(Path(tmp))
            self.assertEqual(report['status'],'BLOCKED_MISSING_SOURCES')
            self.assertFalse(report['bankable'])
    def test_manifest_tamper_fails_even_with_original_workbook(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            new=Path(tmp)
            for name in ('provenance/V20_IMPORT_SHA256.json',
                         'provenance/files.json','provenance/V21_FORMULA_PIN.json',
                         'archive/originals/V15_2/Bering_Corridor_V15_2_Risk_Evidence_Aligned_2026-10-27.xlsx'):
                path=new/name
                path.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(root/name,path)
            original=new/'provenance/V20_IMPORT_SHA256.json'
            value=json.loads(original.read_text(encoding='utf-8'))
            value['status']='SELF_ATTESTED_COMPLETE'
            original.write_text(json.dumps(value),encoding='utf-8')
            report=execute(new)
            self.assertEqual(report['status'],'FAIL_TAMPERED_MANIFEST')
            self.assertFalse(report['checks']['manifest_pinned'])
    def test_complete_staging_is_local_not_remote_certification(self):
        root=Path(__file__).resolve().parents[2]
        if not (root/'archive/originals/V15_2/Bering_Corridor_V15_2_Risk_Evidence_Aligned_2026-10-27.xlsx').exists():
            self.fail('Source pack missing: release admission must FAIL, never skip')
        result=execute(root)
        self.assertEqual(result['status'],'PASS_LOCAL_GIT_SOURCE_AND_SELECTED_MATH_ONLY')
        self.assertEqual(result['checks']['git_blob_count'],42)
        self.assertEqual(result['checks']['formula_count'],493)
        self.assertTrue(result['checks']['independent_223_checks'])
        self.assertFalse(result['bankable'])
        self.assertFalse(result['github_runner_proved'])
        self.assertFalse(result['full_excel_recalculation'])

if __name__=='__main__':unittest.main()
