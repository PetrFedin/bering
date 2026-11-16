"""V35 synthetic-only unit tests; no real bank, client, or issuer evidence."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from v35_evidence_bytes_custody_gate import (check_manifest, private_location, run,
    SCHEMA, NOTICE, ROLES, MAX_FILE_BYTES, report, references)

GOOD33=lambda p:{'status':'STRUCTURAL_REVIEW_REQUIRED'}
GOOD34=lambda p,s,d:{'status':'STRUCTURAL_REVIEW_REQUIRED'}


class SourceBytesTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo=Path(temp.name)
        self.private=self.repo/'local_private'
        self.private.mkdir()
        self.vault=self.private/'v35_vault'
        self.vault.mkdir()
        self.roles={}
        self.rows=[]
        for role in sorted(ROLES):
            content=('SYNTHETIC_NOT_REAL_'+role).encode()
            sha=hashlib.sha256(content).hexdigest()
            name='sources/'+role.lower()+'.txt'
            p=self.vault/name
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(content)
            self.roles[role]=(p,sha)
            self.rows.append({'role':role,'sha256':sha,
                              'relative_path':name,'byte_length':len(content)})
        sha=lambda role:self.roles[role][1]
        self.v33={'monthly_coverage':[{'attestation_sha256':sha('MONTH_ATTESTATION')}],
                  'shipments':[{'source_sha256':sha('OD_EXTRACT'),
                                'waybill_sha256':sha('WAYBILL'),
                                'receipt_sha256':sha('RECEIPT'),
                                'invoice_sha256':sha('INVOICE'),
                                'bank_statement_sha256':sha('BANK_STATEMENT')}]}
        self.sha33='a'*64
        self.sha34='b'*64
        self.v34={'v33_source_sha256':self.sha33,
                  'invoices':[{'invoice_sha256':sha('INVOICE'),
                               'credit_note_sha256':sha('CREDIT_NOTE')}],
                  'bank_transactions':[{'bank_statement_sha256':sha('BANK_STATEMENT')}]}
        self.m={'schema':SCHEMA,'notice':NOTICE,'v33_sha256':self.sha33,
                'v34_sha256':self.sha34,'evidence':copy.deepcopy(self.rows)}

    def check(self):
        return check_manifest(self.m,self.v33,self.v34,self.vault,self.sha33,self.sha34,
                              validate_v33=GOOD33,validate_v34=GOOD34)

    def invalid(self,code=None):
        r=self.check()
        self.assertEqual(r['status'],'INVALID',r['errors'])
        self.assertFalse(r['investment_approved'])
        self.assertIsNone(r['paid_incremental_40ft'])
        if code:self.assertIn(code,r['errors'])

    def row(self,role):
        return next(x for x in self.m['evidence'] if x['role']==role)

    def test_success_is_byte_only_not_bank_original(self):
        r=self.check()
        self.assertEqual(r['status'],'LOCAL_BYTES_MATCH_ONLY',r['errors'])
        self.assertEqual(r['local_source_files_with_recomputed_matching_sha256'],7)
        self.assertEqual(r['referenced_document_role_pairs_checked'],9)
        for f in ('original_issuer_verified','signed_document_verified',
                  'source_row_content_verified','bank_settlement_verified',
                  'od_additionality_verified','github_hosted_ci_green',
                  'bankable_revenue_approved','investment_approved'):
            self.assertFalse(r[f])
        self.assertIsNone(r['bering_npv_rub'])

    def test_reference_cardinality_document_roles(self):
        refs,count=references(self.v33,self.v34)
        self.assertEqual(len(refs),7)
        self.assertEqual(count,9)

    def test_no_inputs_is_not_zero_volume(self):
        r=run(self.repo)
        self.assertEqual(r['status'],'NO_PRIVATE_SOURCE_RECORDS')
        self.assertIsNone(r['paid_incremental_40ft'])
        self.assertIsNone(r['local_source_files_with_recomputed_matching_sha256'])

    def test_any_missing_input_fails_closed(self):
        r=run(self.repo,manifest_path=self.private/'x.json')
        self.assertEqual(r['status'],'INVALID')
        self.assertIn('ALL_PRIVATE_INPUTS_REQUIRED',r['errors'])

    def test_wrong_notice_rejected(self):
        self.m['notice']='BANK_CERTIFIED'
        self.invalid('INVALID_SOURCE_NOTICE')

    def test_fake_v33_sha_rejected(self):
        self.m['v33_sha256']='0'*64
        self.invalid('V33_SHA256_MISMATCH')

    def test_fake_v34_sha_rejected(self):
        self.m['v34_sha256']='f'*64
        self.invalid('V34_SHA256_MISMATCH')

    def test_v34_points_to_other_v33(self):
        self.v34['v33_source_sha256']='0'*64
        self.invalid('V34_V33_LINK_MISMATCH')

    def test_bad_v33_validation_rejected(self):
        r=check_manifest(self.m,self.v33,self.v34,self.vault,self.sha33,self.sha34,
                         validate_v33=lambda x:{'status':'INVALID'},validate_v34=GOOD34)
        self.assertIn('V33_STRUCTURAL_CHECK_FAILED',r['errors'])

    def test_bad_v34_validation_rejected(self):
        r=check_manifest(self.m,self.v33,self.v34,self.vault,self.sha33,self.sha34,
                         validate_v33=GOOD33,validate_v34=lambda p,s,d:{'status':'INVALID'})
        self.assertIn('V34_STRUCTURAL_CHECK_FAILED',r['errors'])

    def test_missing_integrated_validators_fails_closed(self):
        r=check_manifest(self.m,self.v33,self.v34,self.vault,self.sha33,self.sha34)
        self.assertEqual(r['status'],'INVALID')
        self.assertIn('INTEGRATED_VALIDATORS_NOT_AVAILABLE',r['errors'])

    def test_missing_bank_statement(self):
        self.row('BANK_STATEMENT')
        self.m['evidence']=[x for x in self.m['evidence'] if x['role']!='BANK_STATEMENT']
        self.invalid('REFERENCED_SOURCE_MISSING')

    def test_unreferenced_extra_document(self):
        c=b'fake_extra'
        (self.vault/'extra').write_bytes(c)
        self.m['evidence'].append({'role':'INVOICE','sha256':hashlib.sha256(c).hexdigest(),
                                   'relative_path':'extra','byte_length':len(c)})
        self.invalid('UNREFERENCED_SOURCE_SUPPLIED')

    def test_repeated_role_document(self):
        self.m['evidence'].append(copy.deepcopy(self.m['evidence'][0]))
        self.invalid('DUPLICATE_ROLE_AND_DOCUMENT_SHA')

    def test_same_sha_assigned_to_two_roles(self):
        self.m['evidence'][1]['sha256']=self.m['evidence'][0]['sha256']
        self.invalid('SINGLE_FILE_CLAIMED_AS_MULTIPLE_ROLES')

    def test_same_path_assigned_to_two_evidence_items(self):
        self.m['evidence'][1]['relative_path']=self.m['evidence'][0]['relative_path']
        self.invalid('SINGLE_SOURCE_PATH_REUSED')

    def test_overwriting_document_bytes_detected(self):
        p,_=self.roles['INVOICE']
        p.write_bytes(b'CHANGED!')
        self.invalid('SOURCE_SIZE_MISMATCH')

    def test_equal_length_change_detected(self):
        p,_=self.roles['RECEIPT']
        data=p.read_bytes()
        p.write_bytes(b'X'+data[1:])
        self.invalid('SOURCE_SHA_MISMATCH')

    def test_removed_file_rejected(self):
        self.roles['WAYBILL'][0].unlink()
        self.invalid('SOURCE_FILE_MISSING')

    def test_wrong_declared_length_rejected(self):
        self.row('INVOICE')['byte_length']+=1
        self.invalid('SOURCE_SIZE_MISMATCH')

    def test_boolean_length_rejected(self):
        self.row('INVOICE')['byte_length']=True
        self.invalid('EVIDENCE_SIZE_INVALID')

    def test_large_claimed_length_rejected(self):
        self.row('INVOICE')['byte_length']=MAX_FILE_BYTES+1
        self.invalid('EVIDENCE_SIZE_INVALID')

    def test_zero_length_rejected(self):
        self.row('INVOICE')['byte_length']=0
        self.invalid('EVIDENCE_SIZE_INVALID')

    def test_unsupported_role_rejected(self):
        self.m['evidence'][0]['role']='BANK_APPROVED'
        self.invalid('EVIDENCE_ROLE_OR_SHA_INVALID')

    def test_unhashable_role_rejected(self):
        self.m['evidence'][0]['role']=['INVOICE']
        self.invalid('EVIDENCE_ROLE_OR_SHA_INVALID')

    def test_malformed_sha_rejected(self):
        self.row('INVOICE')['sha256']='NOT_A_HASH'
        self.invalid('EVIDENCE_ROLE_OR_SHA_INVALID')

    def test_extra_field_is_rejected(self):
        self.m['evidence'][0]['bank_approved']=True
        self.invalid('EVIDENCE_ROW_SCHEMA_INVALID')

    def test_malformed_root_fields_rejected(self):
        self.m['issuer_approved']=True
        self.invalid('MANIFEST_SCHEMA_INVALID')

    def test_relative_parent_path_rejected(self):
        self.row('INVOICE')['relative_path']='../v33.json'
        self.invalid('UNSAFE_RELATIVE_EVIDENCE_PATH')

    def test_absolute_path_rejected(self):
        self.row('INVOICE')['relative_path']=str(self.roles['INVOICE'][0])
        self.invalid('UNSAFE_RELATIVE_EVIDENCE_PATH')

    def test_windows_backslash_rejected(self):
        self.row('INVOICE')['relative_path']='..\\bank.txt'
        self.invalid('UNSAFE_RELATIVE_EVIDENCE_PATH')

    def test_file_symlink_rejected(self):
        (self.vault/'symlink.txt').symlink_to(self.roles['INVOICE'][0])
        self.row('INVOICE')['relative_path']='symlink.txt'
        self.invalid('SOURCE_SYMLINK_REJECTED')

    def test_dir_symlink_escape_rejected(self):
        (self.vault/'outside').symlink_to(self.private, target_is_directory=True)
        self.row('INVOICE')['relative_path']='outside/v33.json'
        self.invalid('SOURCE_OUTSIDE_VAULT')

    def test_nested_symlink_without_escape_rejected(self):
        (self.vault/'alias').symlink_to(self.vault/'sources', target_is_directory=True)
        self.row('INVOICE')['relative_path']='alias/invoice.txt'
        self.invalid('SOURCE_SYMLINK_REJECTED')

    def test_document_count_cap(self):
        self.m['evidence']*=80
        self.invalid('EVIDENCE_LIST_INVALID')

    def test_rejects_json_shape_when_no_shipments(self):
        self.v33['shipments']=[]
        self.invalid('NO_SHIPMENTS_AND_INVOICES')

    def test_source_line_missing_hash_is_not_a_real_document(self):
        self.v33['shipments'][0]['receipt_sha256']='0'*64
        self.invalid('REFERENCED_SOURCE_MISSING')

    def test_private_location_outside_repo(self):
        with self.assertRaises(ValueError):
            private_location(self.repo,self.repo/'data/waybill.json')

    def test_private_location_missing_file(self):
        with self.assertRaises(ValueError):
            private_location(self.repo,self.private/'unknown.json')

    def test_private_location_symlink_rejected(self):
        src=self.private/'input.json'
        src.write_text('{}')
        symlink=self.private/'alias.json'
        symlink.symlink_to(src)
        with self.assertRaises(ValueError):
            private_location(self.repo,symlink)

    def test_default_cli_does_not_approve_or_expose_data(self):
        cp=subprocess.run([sys.executable,str(ROOT/'scripts/v35_evidence_bytes_custody_gate.py')],
                          cwd=ROOT,capture_output=True,text=True,check=False)
        self.assertEqual(cp.returncode,0,cp.stderr)
        r=json.loads(cp.stdout)
        self.assertEqual(r['status'],'NO_PRIVATE_SOURCE_RECORDS')
        self.assertFalse(r['investment_approved'])
        self.assertNotIn('INVOICE_001',cp.stdout)

    def test_partial_cli_args_rejected(self):
        cp=subprocess.run([sys.executable,str(ROOT/'scripts/v35_evidence_bytes_custody_gate.py'),
                           '--manifest','local_private/manifest.json'],cwd=ROOT,
                          capture_output=True,text=True,check=False)
        self.assertEqual(cp.returncode,2)
        self.assertEqual(json.loads(cp.stdout)['status'],'INVALID')


if __name__=='__main__':
    unittest.main()
