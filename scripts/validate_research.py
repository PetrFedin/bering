#!/usr/bin/env python3
"""Read-only QA of original CSV evidence registers and provenance manifest."""
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "registries"
SHA = ROOT / "provenance" / "SHA256SUMS_available_originals.txt"


def validate_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        head = fh.readline()
        if head.startswith("<PARSED TEXT") or head.startswith("index,"):
            raise ValueError("spreadsheet reader wrapper or index column in CSV")
        delimiter = ";" if head.count(";") > head.count(",") else ","
        fh.seek(0)
        reader = csv.reader(fh, delimiter=delimiter, strict=True)
        rows = iter(reader)
        header = next(rows)
        if not header or len(header)<2 or any(not cell.strip() for cell in header):
            raise ValueError("missing/empty CSV column name")
        count=0
        for i,row in enumerate(rows,2):
            if len(row)!=len(header):
                raise ValueError(f"row {i} has {len(row)} fields; expected {len(header)}")
            count+=1
        return count


def main():
    errors=[];files=0;rows=0
    for path in sorted(REGISTRY.glob("*.csv")):
        try:
            rows+=validate_csv(path);files+=1
        except (ValueError,UnicodeError,csv.Error,OSError,StopIteration) as e:
            errors.append(f"{path}: {e}")
    if files==0:errors.append("No validated CSV registers found")
    if SHA.exists():
        for i,line in enumerate(SHA.read_text(encoding="utf-8").splitlines(),1):
            if not line.strip() or line.startswith("#"):continue
            parts=line.split(maxsplit=1)
            if len(parts)!=2 or not re.fullmatch(r"[0-9a-f]{64}",parts[0]):
                errors.append(f"Malformed SHA-256 row {i}")
    print(f"CSV files={files}, rows={rows}, errors={len(errors)}")
    for err in errors: print(err,file=sys.stderr)
    return int(bool(errors))


if __name__=="__main__":
    sys.exit(main())
