#!/usr/bin/env python3
"""Fail-closed validation of original source files against a SHA manifest.

Hash matching does not attest document authenticity, rights, or commercial truth.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

def verify(root: Path, manifest: dict) -> dict:
    base=root.resolve(strict=True)
    problems=[]
    seen=set()
    files=manifest.get("files")
    if not isinstance(files,list) or len(files)==0:
        return {"checked":0,"passed":0,"errors":["Empty or absent manifest"],"status":"FAIL"}
    for row in files:
        rel=row.get("path")
        expected=row.get("sha256")
        size=row.get("bytes")
        if not isinstance(rel,str) or rel in seen or not isinstance(expected,str) or not re.fullmatch(r"[0-9a-f]{64}",expected):
            problems.append(f"Invalid or duplicate manifest entry: {rel!r}")
            continue
        seen.add(rel)
        try:
            path=(base/rel).resolve(strict=True)
            if not path.is_relative_to(base) or not path.is_file() or path.is_symlink():
                raise ValueError("Unsafe or missing source path")
            h=hashlib.sha256()
            with path.open("rb") as fd:
                for part in iter(lambda:fd.read(1024*1024),b""):
                    h.update(part)
            if h.hexdigest()!=expected or path.stat().st_size!=size:
                raise ValueError("SHA-256 or file-size mismatch")
        except (OSError,ValueError) as e:
            problems.append(f"{rel}: {e}")
    return {"checked":len(files),"passed":len(files)-len(problems),
            "errors":problems,"status":"FAIL" if problems else "LOCAL_BYTES_MATCH",
            "not_a_contract_authenticity_check":True}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    args=ap.parse_args()
    try:
        report=verify(args.root,json.loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError,ValueError) as e:
        print(f"FAILED: {e}")
        return 1
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if not report["errors"] else 1

if __name__=="__main__":
    raise SystemExit(main())
