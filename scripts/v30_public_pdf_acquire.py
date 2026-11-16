#!/usr/bin/env python3
"""Fetch ONE publicly listed MLC project PDF with owner-metadata SHA256 checks.

This utility never certifies design approval, never bypasses rate limits, and
never stores unlicensed raw files in the tracked Git tree. Use a single file per
invocation, stop on HTTP 429 and obtain originals via authorized channels.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ARCHIVE = "https://disk.yandex.ru/d/VBtKSnvIO1rolQ"
MANIFEST = "data/public/V28_MLC_PRIMARY_PROJECT_FILE_MANIFEST.json"
API = "https://cloud-api.yandex.net/v1/disk/public/resources/download"

def select(rows, name):
    exact = [r for r in rows if r["path"] == name]
    if exact:
        return exact[0]
    basename = [r for r in rows if r["path"].rsplit("/", 1)[-1] == name]
    if len(basename) == 1:
        return basename[0]
    if not basename:
        raise ValueError("No matching source path in the pinned owner manifest")
    raise ValueError("Ambiguous filename; use full /archive/path")

def run(repo, name, outdir, dry_run=False):
    repo = Path(repo).resolve()
    manifest = json.loads((repo / MANIFEST).read_text(encoding="utf-8"))
    rows = manifest["documents"]
    assert len(rows) == 52
    entry = select(rows, name)
    suffix = entry["path"].rsplit("/", 1)[-1]
    wanted = entry["sha256_from_public_api"]
    expected_size = entry["bytes"]
    if not suffix.lower().endswith(".pdf") or len(wanted) != 64 or expected_size <= 0:
        raise ValueError("Invalid project PDF entry")
    output_dir = Path(outdir)
    if not output_dir.is_absolute():
        output_dir = repo / output_dir
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(repo / "local_private"):
        raise ValueError("Original PDFs must be stored only under ignored local_private/")
    response = {
        "source_path": entry["path"], "owner_api_sha256": wanted,
        "expected_bytes": expected_size, "downloaded": False,
        "actual_sha256": None, "actual_bytes": None,
        "approved_2026_design_revision_authenticated": False,
        "source_proves_bering_paid_cargo": False,
        "status": "NOT_STARTED" if dry_run else "DOWNLOAD_FAILED"
    }
    if dry_run:
        response["status"] = "DRY_RUN_NO_NETWORK"
        return response
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = suffix
    destination = output_dir / safe_name
    if destination.is_symlink():
        raise ValueError("Unsafe destination symlink")
    if destination.exists():
        raise ValueError("Existing local original will not be silently overwritten")
    query = urllib.parse.urlencode({"public_key": ARCHIVE, "path": entry["path"]})
    try:
        req = urllib.request.Request(API + "?" + query, headers={"User-Agent": "BeringSourceCheckV30/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response_file:
            link = json.load(response_file).get("href")
        if not isinstance(link, str) or not link.startswith("https://"):
            raise ValueError("Public API did not supply an HTTPS resource")
        hashvalue = hashlib.sha256()
        length = 0
        with tempfile.NamedTemporaryFile(prefix=".v30-", suffix=".part", dir=output_dir, delete=False) as tmp:
            temp_path = Path(tmp.name)
        try:
            request = urllib.request.Request(link, headers={"User-Agent": "BeringSourceCheckV30/1.0"})
            with urllib.request.urlopen(request, timeout=80) as upstream, temp_path.open("wb") as fd:
                for block in iter(lambda: upstream.read(1024 * 1024), b""):
                    length += len(block)
                    if length > expected_size:
                        raise ValueError("Downloaded file exceeds owner-declared length")
                    fd.write(block)
                    hashvalue.update(block)
            actual = hashvalue.hexdigest()
            response.update(actual_sha256=actual, actual_bytes=length)
            if length != expected_size or actual != wanted:
                raise ValueError("SHA256 or size disagrees with public owner metadata")
            os.replace(temp_path, destination)
            response.update(downloaded=True, status="PUBLIC_BYTES_SHA256_MATCH_OWNER")
        finally:
            temp_path.unlink(missing_ok=True)
    except urllib.error.HTTPError as exc:
        response["status"] = "RATE_LIMITED_NO_RETRY" if exc.code == 429 else "HTTP_ERROR_" + str(exc.code)
    except (OSError, ValueError, TimeoutError) as exc:
        response["status"] = "FETCH_REJECTED_" + type(exc).__name__
    return response

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--name", help="Exact PDF basename, or full /archive/path")
    parser.add_argument("--outdir", default="local_private/v30_public_pdfs")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        if args.list:
            reg = json.loads((args.repo / MANIFEST).read_text(encoding="utf-8"))
            for entry in reg["documents"]:
                print(entry["path"])
            return 0
        if not args.name:
            parser.error("--name is mandatory unless --list is used")
        result = run(args.repo, args.name, args.outdir, args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] in ("DRY_RUN_NO_NETWORK", "PUBLIC_BYTES_SHA256_MATCH_OWNER") else 2
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "INVALID", "reason": type(exc).__name__, "source_proves_bering_paid_cargo": False,
                          "approved_2026_design_revision_authenticated": False}, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
