#!/usr/bin/env python3
"""Reproducible source/selected-math admission; NOT full formula recalc or investment approval.

For eventual GitHub CI: the runner must first clone the repository with the 42
originals committed. If they are absent, this script fails rather than skips.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from formula_fingerprint import assess,scan
from verify_git_origins import inspect_repository

EXPECTED_MANIFEST_SHA256='cc97918f23c8590189e078f9e09a54682404943bfc675a4b47e1c334702b945a'
EXPECTED_LEDGER_SHA256='240353feee7e34921f5399113f8027d70110dcc9ff0ca5ecee1f846c1efbeb9b'

def sha256(path:Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def execute(repo:Path)->dict:
    repo=repo.resolve()
    failures=[]
    parts={}
    manifest=repo/'provenance/V20_IMPORT_SHA256.json'
    ledger=repo/'provenance/files.json'
    pin=repo/'provenance/V21_FORMULA_PIN.json'
    book=repo/'archive/originals/V15_2/Bering_Corridor_V15_2_Risk_Evidence_Aligned_2026-10-27.xlsx'
    required=(manifest,ledger,pin,book)
    absent=[str(p.relative_to(repo)) for p in required if not p.is_file()]
    if absent:
        return {'status':'BLOCKED_MISSING_SOURCES','missing':absent,'checks':parts,
                'bankable':False,'github_runner_proved':False}
    parts['manifest_pinned']=sha256(manifest)==EXPECTED_MANIFEST_SHA256
    parts['ledger_pinned']=sha256(ledger)==EXPECTED_LEDGER_SHA256
    if not parts['manifest_pinned'] or not parts['ledger_pinned']:
        return {'status':'FAIL_TAMPERED_MANIFEST','checks':parts,
                'bankable':False,'github_runner_proved':False}
    originals=inspect_repository(repo,json.loads(manifest.read_text(encoding='utf-8')),
                                 expected_count=42)
    parts['git_blob_integrity']=originals['status']=='PASS_COMMITTED_ORIGINALS'
    parts['git_blob_count']=originals['passed']
    if not parts['git_blob_integrity']:
        failures.extend(originals['errors'][:10])
    fingerprint=assess(scan(book),json.loads(pin.read_text(encoding='utf-8')))
    parts['formula_lineage']=fingerprint['status']=='PASS_FORMULA_LINEAGE_ONLY'
    parts['formula_count']=fingerprint['observation']['formula_count']
    parts['formula_cache_missing_count']=fingerprint['observation']['missing_caches']
    if not parts['formula_lineage']:
        failures.append('Pinned formula fingerprint mismatch')
    if not failures:
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'financial_tieout.json'
            cmd=[sys.executable,str(repo/'scripts/independent_financial_tieout.py'),
                 '--book',str(book),'--expected-sha256',sha256(book),
                 '--manifest',str(ledger),'--root',str(repo),'--output',str(output)]
            proc=subprocess.run(cmd,cwd=repo,stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,text=True)
            if proc.returncode != 0 or not output.is_file():
                failures.append('Independent financial tieout failed: '+proc.stderr[-600:])
            else:
                report=json.loads(output.read_text(encoding='utf-8'))
                summary=report.get('summary') or {}
                archives=report.get('source_archive') or {}
                parts['independent_223_checks']=(summary.get('tests')==223 and
                                                summary.get('passed')==223 and
                                                summary.get('failed')==0)
                parts['source_31_checks']=(archives.get('files')==31 and
                                           archives.get('passed')==31 and
                                           archives.get('all_pass') is True)
                parts['financial_source_pinned']=report.get('source_sha256')==sha256(book)
                if not all(parts[k] for k in ('independent_223_checks',
                        'source_31_checks','financial_source_pinned')):
                    failures.append('Independent mathematical / 31-source audit incomplete')
    return {'status':'PASS_LOCAL_GIT_SOURCE_AND_SELECTED_MATH_ONLY' if not failures else 'FAIL',
            'checks':parts,'errors':failures,
            'bankable':False,'full_excel_recalculation':False,
            'github_runner_proved':False,
            'note':'GitHub CI must independently run this on an authorized checked-out SHA to certify remote reproducibility.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--out',type=Path);args=p.parse_args()
    report=execute(args.repo)
    rendered=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.out:args.out.write_text(rendered,encoding='utf-8')
    print(rendered)
    return 0 if report['status']=='PASS_LOCAL_GIT_SOURCE_AND_SELECTED_MATH_ONLY' else 1

if __name__=='__main__':raise SystemExit(main())
