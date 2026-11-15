#!/usr/bin/env python3
"""Research-only V35: bind claimed V33/V34 SHA references to local source bytes.

This cannot authenticate issuers/signatures, original source-row contents, actual
bank settlements, additional cargo, or NPV. Never uploads local_private data.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 'BERING_V35_LOCAL_SOURCE_BYTES_V1'
NOTICE = 'OWNER_SUPPLIED_BYTES_NOT_AUTHENTICATED_BY_BANK_OR_ISSUER'
MANIFEST_FIELDS = {'schema','notice','v33_sha256','v34_sha256','evidence'}
ENTRY_FIELDS = {'role','sha256','relative_path','byte_length'}
ROLES = frozenset({'MONTH_ATTESTATION','OD_EXTRACT','WAYBILL','RECEIPT',
                   'INVOICE','BANK_STATEMENT','CREDIT_NOTE'})
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
MAX_MANIFEST_ITEMS = 500
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_JSON_BYTES = 40 * 1024 * 1024
REFERENCES = {'source_sha256': 'OD_EXTRACT','waybill_sha256':'WAYBILL',
              'receipt_sha256':'RECEIPT','invoice_sha256':'INVOICE',
              'bank_statement_sha256':'BANK_STATEMENT'}


def valid_sha(value):
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def report(status, errors, **values):
    return {
        'schema':SCHEMA,'status':status,
        'local_source_files_with_recomputed_matching_sha256':values.get('files'),
        'referenced_document_role_pairs_checked':values.get('refs'),
        'local_bytes_checked':values.get('bytes'),
        'original_issuer_verified':False,'signed_document_verified':False,
        'source_row_content_verified':False,'bank_settlement_verified':False,
        'od_additionality_verified':False,'github_hosted_ci_green':False,
        'paid_incremental_40ft':None,'group_incremental_cm_rub':None,
        'bering_npv_rub':None,'P1':'HOLD','P2':'HOLD','P3':'HOLD',
        'bankable_revenue_approved':False,'investment_approved':False,
        'errors':sorted(set(errors)),
        'limitations':('Matching local SHA256 checks byte equality against the provided digest only; '
                       'not independent issuer, bank, signature, source-row or payment proof.')
    }


def private_location(repo, arg, directory=False):
    """Reject traversal/symlinks at every component inside git-ignored local_private."""
    root = Path(repo).resolve()
    private = root / 'local_private'
    path = Path(arg)
    if not path.is_absolute():
        path = root / path
    try:
        rel = path.relative_to(private)
    except ValueError as err:
        raise ValueError('OUTSIDE_LOCAL_PRIVATE') from err
    if not rel.parts or '..' in rel.parts or any(x == '' for x in rel.parts):
        raise ValueError('UNSAFE_PRIVATE_PATH')
    for component in (private, *(private.joinpath(*rel.parts[:i])
                                 for i in range(1,len(rel.parts)+1))):
        if component.is_symlink():
            raise ValueError('PRIVATE_SYMLINK_REJECTED')
    if not private.is_dir() or not path.resolve().is_relative_to(private.resolve()):
        raise ValueError('NO_PRIVATE_TREE_OR_ESCAPE')
    if directory:
        if not path.is_dir():
            raise ValueError('PRIVATE_DIRECTORY_ABSENT')
    elif not path.is_file() or not 0 < path.stat().st_size <= MAX_JSON_BYTES:
        raise ValueError('PRIVATE_INPUT_ABSENT_OR_TOO_LARGE')
    return path


def references(v33,v34):
    """All claimed document roles must have a corresponding byte-level source."""
    actual = set()
    uses = 0
    for row in v33['monthly_coverage']:
        actual.add(('MONTH_ATTESTATION',row['attestation_sha256']))
        uses += 1
    for row in v33['shipments']:
        for column, role in REFERENCES.items():
            actual.add((role,row[column]))
            uses += 1
    for row in v34['invoices']:
        actual.add(('INVOICE',row['invoice_sha256']))
        uses += 1
        if row['credit_note_sha256'] is not None:
            actual.add(('CREDIT_NOTE',row['credit_note_sha256']))
            uses += 1
    for row in v34['bank_transactions']:
        actual.add(('BANK_STATEMENT',row['bank_statement_sha256']))
        uses += 1
    return actual, uses


def check_manifest(m, v33, v34, vault, v33_sha, v34_sha,
                   validate_v33=None, validate_v34=None):
    errors = []
    if not isinstance(m,dict) or set(m)!=MANIFEST_FIELDS:
        return report('INVALID',['MANIFEST_SCHEMA_INVALID'])
    if m.get('schema')!=SCHEMA or m.get('notice')!=NOTICE:
        errors.append('INVALID_SOURCE_NOTICE')
    if not valid_sha(m.get('v33_sha256')) or m['v33_sha256']!=v33_sha:
        errors.append('V33_SHA256_MISMATCH')
    if not valid_sha(m.get('v34_sha256')) or m['v34_sha256']!=v34_sha:
        errors.append('V34_SHA256_MISMATCH')
    if not isinstance(v33,dict) or not isinstance(v34,dict):
        return report('INVALID',errors+['V33_V34_NOT_OBJECTS'])
    if v34.get('v33_source_sha256')!=v33_sha:
        errors.append('V34_V33_LINK_MISMATCH')
    # In production these must be the actual V33/V34 validators. Synthetic tests
    # may inject functions to test only this gate; they don't prove integration.
    if validate_v33 is None or validate_v34 is None:
        return report('INVALID',errors+['INTEGRATED_VALIDATORS_NOT_AVAILABLE'])
    try:
        v33_result=validate_v33(v33)
        v34_result=validate_v34(v34,v33,v33_sha)
        if v33_result.get('status')!='STRUCTURAL_REVIEW_REQUIRED':
            errors.append('V33_STRUCTURAL_CHECK_FAILED')
        if v34_result.get('status')!='STRUCTURAL_REVIEW_REQUIRED':
            errors.append('V34_STRUCTURAL_CHECK_FAILED')
    except (KeyError,TypeError,ValueError,IndexError):
        return report('INVALID',errors+['V33_V34_VALIDATION_FAILED'])
    if errors:
        return report('INVALID',errors)
    rows=m.get('evidence')
    if not isinstance(rows,list) or len(rows)>MAX_MANIFEST_ITEMS:
        return report('INVALID',['EVIDENCE_LIST_INVALID'])
    try:
        expected,use_count=references(v33,v34)
    except (KeyError,TypeError,ValueError):
        return report('INVALID',['SOURCE_DOCUMENT_REFERENCES_MALFORMED'])
    if not rows or not v33['shipments'] or not v34['invoices']:
        errors.append('NO_SHIPMENTS_AND_INVOICES')
    observed=set()
    sha_role={}
    observed_paths=set()
    actual_bytes=0
    valid_count=0
    for row in rows:
        if not isinstance(row,dict) or set(row)!=ENTRY_FIELDS:
            errors.append('EVIDENCE_ROW_SCHEMA_INVALID')
            continue
        role,sha,name,nbytes=(row[k] for k in ('role','sha256','relative_path','byte_length'))
        if not isinstance(role,str) or role not in ROLES or not valid_sha(sha):
            errors.append('EVIDENCE_ROLE_OR_SHA_INVALID')
            continue
        pair=role,sha
        if pair in observed:
            errors.append('DUPLICATE_ROLE_AND_DOCUMENT_SHA')
            continue
        observed.add(pair)
        if sha in sha_role and sha_role[sha]!=role:
            errors.append('SINGLE_FILE_CLAIMED_AS_MULTIPLE_ROLES')
        sha_role[sha]=role
        if not isinstance(name,str) or not name or '\\' in name:
            errors.append('UNSAFE_RELATIVE_EVIDENCE_PATH')
            continue
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or any(x=='' for x in rel.parts):
            errors.append('UNSAFE_RELATIVE_EVIDENCE_PATH')
            continue
        if name in observed_paths:
            errors.append('SINGLE_SOURCE_PATH_REUSED')
        observed_paths.add(name)
        if type(nbytes)!=int or not 0<nbytes<=MAX_FILE_BYTES:
            errors.append('EVIDENCE_SIZE_INVALID')
            continue
        path=Path(vault)/rel
        if not path.resolve().is_relative_to(Path(vault).resolve()):
            errors.append('SOURCE_OUTSIDE_VAULT')
            continue
        if any((Path(vault).joinpath(*rel.parts[:i])).is_symlink()
               for i in range(1,len(rel.parts)+1)):
            errors.append('SOURCE_SYMLINK_REJECTED')
            continue
        if not path.is_file():
            errors.append('SOURCE_FILE_MISSING')
            continue
        if path.stat().st_size!=nbytes:
            errors.append('SOURCE_SIZE_MISMATCH')
            continue
        if digest(path)!=sha:
            errors.append('SOURCE_SHA_MISMATCH')
            continue
        actual_bytes+=nbytes
        valid_count+=1
    if expected-observed:
        errors.append('REFERENCED_SOURCE_MISSING')
    if observed-expected:
        errors.append('UNREFERENCED_SOURCE_SUPPLIED')
    return report('INVALID' if errors else 'LOCAL_BYTES_MATCH_ONLY',errors,
                  files=valid_count if not errors else None,
                  refs=use_count if not errors else None,
                  bytes=actual_bytes if not errors else None)


def run(repo, manifest_path=None, v33_path=None, v34_path=None, vault_path=None):
    args=(manifest_path,v33_path,v34_path,vault_path)
    if all(arg is None for arg in args):
        return report('NO_PRIVATE_SOURCE_RECORDS',[])
    if any(arg is None for arg in args):
        return report('INVALID',['ALL_PRIVATE_INPUTS_REQUIRED'])
    try:
        root=Path(repo).resolve()
        paths=[private_location(root,arg) for arg in args[:3]]
        vault=private_location(root,vault_path,directory=True)
        if len({p.resolve() for p in paths})!=3 or any(p.resolve().is_relative_to(vault.resolve()) for p in paths):
            raise ValueError('JSON_INPUT_DUPLICATED_OR_INSIDE_VAULT')
        b33,b34=paths[1].read_bytes(),paths[2].read_bytes()
        m=json.loads(paths[0].read_text(encoding='utf-8'))
        v33=json.loads(b33.decode('utf-8'))
        v34=json.loads(b34.decode('utf-8'))
        # Same source modules as the full Bering checkout; no fallback to fake
        # implementations in production. Explicit import failure remains INVALID.
        from v33_shipment_proof_quality import analyze as check_v33
        from v34_bank_allocation_gate import analyze as check_v34
        return check_manifest(m,v33,v34,vault,
            hashlib.sha256(b33).hexdigest(),hashlib.sha256(b34).hexdigest(),
            validate_v33=check_v33,
            validate_v34=lambda p,s,d:check_v34(p,v33=s,v33_digest=d))
    except (ImportError,OSError,ValueError,UnicodeError,KeyError,TypeError):
        return report('INVALID',['PRIVATE_INPUT_OR_DEPENDENCY_REJECTED'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path('.'))
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--v33',type=Path)
    parser.add_argument('--v34',type=Path)
    parser.add_argument('--vault',type=Path)
    parser.add_argument('--out',type=Path)
    a=parser.parse_args()
    result=run(a.repo,a.manifest,a.v33,a.v34,a.vault)
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.out:
        a.out.write_text(output,encoding='utf-8')
    print(output,end='')
    return 2 if result['status']=='INVALID' else 0


if __name__=='__main__':
    raise SystemExit(main())
