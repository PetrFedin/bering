#!/usr/bin/env python3
"""Read-only QA for public research registry CSVs and the provenance files.
No network activity or modification of source spreadsheets.
"""
from pathlib import Path
import csv, re, sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = ROOT / "data" / "registries"
HEX = re.compile(r"^[0-9a-f]{64}$")

def dialect_and_rows(path):
    text = path.read_text(encoding="utf-8-sig")
    preview = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(preview, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return list(csv.reader(text.splitlines(), dialect=dialect))

def main():
    files=sorted(REGISTRIES.glob("*.csv"))
    failures=[]
    scanned=0
    for path in files:
        try:
            rows=dialect_and_rows(path)
            if not rows or len(rows[0]) < 2:
                failures.append(f"{path}: no parseable header")
                continue
            scanned+=len(rows)-1
            if any(not row for row in rows):
                failures.append(f"{path}: empty rows")
        except Exception as e:
            failures.append(f"{path}: {e}")
    manifest=ROOT / "provenance" / "SHA256SUMS_available_originals.txt"
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or not line.strip():
                continue
            chunks=line.split(None,1)
            if len(chunks)!=2 or not HEX.fullmatch(chunks[0]):
                failures.append("Malformed SHA256 manifest row: "+line[:80])
    print(f"CSV files={len(files)} records={scanned} errors={len(failures)}")
    for issue in failures:print(issue,file=sys.stderr)
    return bool(failures)
if __name__=="__main__":
    sys.exit(main())
