import sys
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from formula_fingerprint import scan, assess
from verify_git_origins import inspect_repository, git_blob_sha1

class FormulaLineageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.book=Path(__file__).resolve().parents[2]/'archive/originals/V15_2/Bering_Corridor_V15_2_Risk_Evidence_Aligned_2026-10-27.xlsx'
        cls.expected=Path(__file__).resolve().parents[2]/'provenance/V21_FORMULA_PIN.json'
        cls.has_source=cls.book.exists() and cls.expected.exists()
    def test_model_release_formula_fingerprint(self):
        self.assertTrue(self.has_source, 'P0: Original V15.2 workbook and manifest MUST be imported; no skip')
        report=assess(scan(self.book),json.loads(self.expected.read_text(encoding='utf-8')))
        self.assertEqual(report['status'],'PASS_FORMULA_LINEAGE_ONLY')
    def test_changed_formula_detected_even_if_cached_value_unchanged(self):
        self.assertTrue(self.has_source, 'P0 original missing')
        from zipfile import ZipFile
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as d:
            tampered=Path(d)/'tampered.xlsx'
            with ZipFile(self.book) as src, ZipFile(tampered,'w') as dst:
                for info in src.infolist():
                    raw=src.read(info.filename)
                    if info.filename=='xl/worksheets/sheet44.xml':
                        root=ET.fromstring(raw)
                        ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                        c=next(z for z in root.findall('.//x:c',ns) if z.get('r')=='L8')
                        f=c.find('x:f',ns)
                        self.assertIsNotNone(f)
                        f.text='1+1' # leave <v> unchanged, so a cached-only check can be fooled
                        raw=ET.tostring(root,encoding='utf-8',xml_declaration=True)
                    dst.writestr(info,raw)
            observation=scan(tampered)
            expected=json.loads(self.expected.read_text(encoding='utf-8'))
            result=assess(observation,expected)
            self.assertEqual(result['status'],'FAIL')
            self.assertFalse(result['checks']['formula_sha256'])
    def test_forged_baseline_does_not_pass(self):
        fake={'workbook_sha256':'A','formula_sha256':'B','formula_count':493,'sheet_count':72,
              'missing_caches':35,'missing_caches_sha256':'C','sheet_names_sha256':'D',
              'external_link_formulas':[],'embedded_formula_ref_errors':[],
              'hidden_sheets':[], 'pilot_gate_caches': {'test':{'N5':'HOLD'}}}
        self.assertEqual(assess(fake,{'workbook_sha256':'different'})['status'],'FAIL')
    def test_incomplete_gate_set_is_not_a_valid_hold(self):
        fake={'workbook_sha256':'A','formula_sha256':'B','formula_count':493,'sheet_count':72,
              'missing_caches':35,'missing_caches_sha256':'C','sheet_names_sha256':'D',
              'external_link_formulas':[],'embedded_formula_ref_errors':[],
              'hidden_sheets':[], 'pilot_gate_caches': {'test':{'N5':'HOLD'}}}
        exp={k:fake[k] for k in ('workbook_sha256','formula_sha256','formula_count','sheet_count','missing_caches','missing_caches_sha256','sheet_names_sha256')}
        result=assess(fake,exp)
        self.assertEqual(result['status'],'FAIL')
        self.assertFalse(result['checks']['three_pilots_hold'])
    def test_ready_pilot_fails_acceptance(self):
        fake={'workbook_sha256':'A','formula_sha256':'B','formula_count':493,'sheet_count':72,
              'missing_caches':35,'missing_caches_sha256':'C','sheet_names_sha256':'D',
              'external_link_formulas':[],'embedded_formula_ref_errors':[],
              'hidden_sheets':[], 'pilot_gate_caches': {'test':{'N5':'READY'}}}
        exp={k:fake[k] for k in ('workbook_sha256','formula_sha256','formula_count','sheet_count','missing_caches','missing_caches_sha256','sheet_names_sha256')}
        self.assertEqual(assess(fake,exp)['status'],'FAIL')

class GitBlobTest(unittest.TestCase):
    def _cmd(self,repo,*args):
        return subprocess.run(['git','-C',str(repo),*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_git_blob_hash_matches_git_hash_object(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'binary.dat';p.write_bytes(b'\x00\xffBering\n')
            result=subprocess.run(['git','hash-object',str(p)],check=True,stdout=subprocess.PIPE,text=True)
            self.assertEqual(result.stdout.strip(),git_blob_sha1(p.read_bytes()))
    def test_not_committed_fails_even_when_file_exists(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self._cmd(p,'init','-q')
            self._cmd(p,'-c','user.name=QA','-c','user.email=qa@example.com','commit','-q','--allow-empty','-m','init')
            path=p/'archive/originals/V15_2/demo.xlsx';path.parent.mkdir(parents=True)
            path.write_bytes(b'demo')
            record={'files':[{'path':'archive/originals/V15_2/demo.xlsx','bytes':4,
                              'sha256':__import__('hashlib').sha256(b'demo').hexdigest()}]}
            result=inspect_repository(p,record,expected_count=1)
            self.assertEqual(result['status'],'FAIL')
            self.assertIn('NOT_COMMITTED',str(result['errors']))
    def test_committed_verified_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self._cmd(p,'init','-q')
            path=p/'archive/originals/V15_2/demo.xlsx';path.parent.mkdir(parents=True)
            path.write_bytes(b'ZIP\x00\xff')
            self._cmd(p,'add','.')
            self._cmd(p,'-c','user.name=QA','-c','user.email=qa@example.com','commit','-q','-m','binary')
            record={'files':[{'path':'archive/originals/V15_2/demo.xlsx','bytes':5,
                              'sha256':__import__('hashlib').sha256(b'ZIP\x00\xff').hexdigest()}]}
            result=inspect_repository(p,record,expected_count=1)
            self.assertEqual(result['status'],'PASS_COMMITTED_ORIGINALS')
    def test_partial_archive_does_not_pass_complete_check(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self._cmd(p,'init','-q')
            path=p/'archive/originals/V15_2/demo.xlsx';path.parent.mkdir(parents=True)
            path.write_bytes(b'x')
            self._cmd(p,'add','.')
            self._cmd(p,'-c','user.name=QA','-c','user.email=qa@example.com','commit','-q','-m','single')
            record={'files':[{'path':'archive/originals/V15_2/demo.xlsx','bytes':1,
                              'sha256':__import__('hashlib').sha256(b'x').hexdigest()}]}
            self.assertEqual(inspect_repository(p,record)['status'],'FAIL')
            self.assertEqual(inspect_repository(p,record,expected_count=1)['status'],'PASS_COMMITTED_ORIGINALS')
    def test_modified_worktree_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);self._cmd(p,'init','-q')
            path=p/'archive/originals/V15_2/demo.xlsx';path.parent.mkdir(parents=True)
            path.write_bytes(b'abc')
            self._cmd(p,'add','.')
            self._cmd(p,'-c','user.name=QA','-c','user.email=qa@example.com','commit','-q','-m','binary')
            path.write_bytes(b'abd')
            record={'files':[{'path':'archive/originals/V15_2/demo.xlsx','bytes':3,
                              'sha256':__import__('hashlib').sha256(b'abc').hexdigest()}]}
            result=inspect_repository(p,record,expected_count=1)
            self.assertEqual(result['status'],'FAIL')

if __name__=='__main__':unittest.main()
