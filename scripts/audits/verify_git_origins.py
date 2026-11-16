#!/usr/bin/env python3
"""Check exact source bytes are actually committed as Git blobs, not just zipped.

Requires a local checkout of the GitHub repository with originals imported.
This does not connect to GitHub, assess redistribution rights or authenticate deals.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

def git_blob_sha1(source:bytes)->str:
    return hashlib.sha1(f'blob {len(source)}\0'.encode('ascii')+source).hexdigest()

def inspect_repository(repo:Path, manifest:dict, ref='HEAD', expected_count=42)->dict:
    repo=repo.resolve()
    cmd=['git','-C',str(repo),'ls-tree','-r','-z',ref]
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    recorded={}
    for element in result.stdout.split(b'\0'):
        if not element:continue
        left,path=element.split(b'\t',1)
        mode,obj_type,obj_sha=left.decode('utf-8').split()
        recorded[path.decode('utf-8')]={'mode':mode,'type':obj_type,'sha1':obj_sha}
    entries=manifest.get('files')
    failures=[];validated=0
    if not isinstance(entries,list) or not entries:
        failures.append('Empty manifest')
        entries=[]
    seen=set()
    approved=('archive/originals/','data/registries/','audit/','scripts/audits/','tools/','provenance/')
    if len(entries)!=expected_count:
        failures.append(f'Incomplete original manifest: {len(entries)} entries, expected {expected_count}')
    for entry in entries:
        if not isinstance(entry,dict):
            failures.append('Invalid manifest row type');continue
        path=entry.get('path','')
        if not isinstance(path,str) or path in seen or not path.startswith(approved) or '..' in Path(path).parts or Path(path).is_absolute():
            failures.append(f'Invalid or duplicate original path: {path!r}');continue
        seen.add(path)
        if path not in recorded:
            failures.append(f'NOT_COMMITTED: {path}');continue
        obj=recorded[path]
        if obj['type']!='blob' or obj['mode']!='100644':
            failures.append(f'Wrong Git object type/mode: {path}');continue
        full=(repo/path).resolve()
        if not full.is_relative_to(repo) or not full.is_file():
            failures.append(f'File missing from checkout: {path}');continue
        raw=full.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry.get('sha256') or len(raw)!=entry.get('bytes'):
            failures.append(f'Local file differs from original manifest: {path}');continue
        calculated=git_blob_sha1(raw)
        if calculated!=obj['sha1']:
            failures.append(f'Working tree differs from committed blob: {path}');continue
        validated+=1
    return {'status':'PASS_COMMITTED_ORIGINALS' if not failures else 'FAIL',
            'checked':len(entries),'passed':validated,'errors':failures,
            'ref':ref,'not_proof_of_source_authenticity':True}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--ref',default='HEAD')
    p.add_argument('--expected-count',type=int,default=42)
    a=p.parse_args()
    result=inspect_repository(a.repo,json.loads(a.manifest.read_text(encoding='utf-8')),a.ref,expected_count=a.expected_count)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['status'].startswith('PASS') else 1

if __name__=='__main__':raise SystemExit(main())
