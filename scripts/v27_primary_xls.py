#!/usr/bin/env python3
"""Fetch and inventory original publicly posted MP1/MP2 .xls documents.

Source downloads occur on the CI runner only. Never infer a container volume
from arbitrary adjacent spreadsheet cells. Extraction is a candidate index, not
an accepted statistic. The program does not execute spreadsheet formulas/macros.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler

OLE_MAGIC = bytes.fromhex('d0cf11e0a1b11ae1')
MAX_BYTES = 2_500_000
MAX_CELLS = 1_000_000
PATTERN = re.compile(r'(?:container|cargo|tonnage|tons|tonnes|cargo handling|kontainer|gruz|pereval|konteyner|\\u043a\\u043e\\u043d\\u0442\\u0435\\u0439\\u043d\\u0435\\u0440|\\u0433\\u0440\\u0443\\u0437|\\u043f\\u0435\\u0440\\u0435\\u0432\\u0430\\u043b|\\u0442\\u043e\\u043d\\u043d)', re.I)
OFFICIAL = {
    'MP1_2026_9M': ('https://magadanport.ru/wp-content/uploads/2026/10/MP10014726.xls', '2026-09-30'),
    'MP2_2026_9M': ('https://magadanport.ru/wp-content/uploads/2026/10/MP20014726.xls', '2026-09-30'),
    'MP1_2025_9M': ('https://magadanport.ru/wp-content/uploads/2025/10/MP10014725.xls', '2025-09-30'),
    'MP2_2025_9M': ('https://magadanport.ru/wp-content/uploads/2025/10/MP20014725.xls', '2025-09-30'),
}


def admissible_url(url: str) -> bool:
    p = urlparse(url)
    return (p.scheme == 'https' and p.hostname in {'magadanport.ru', 'www.magadanport.ru'}
            and p.port is None and p.username is None and p.password is None
            and p.path.startswith('/wp-content/uploads/') and p.path.endswith('.xls')
            and not p.params and not p.query and not p.fragment)


class HostRestrictedRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not admissible_url(newurl):
            raise ValueError('redirect leaves official fixed XLS origin')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def get_public_xls(url: str, *, timeout: int = 25) -> bytes:
    if not admissible_url(url):
        raise ValueError('unapproved source URL')
    req = Request(url, headers={'User-Agent': 'BeringResearchIntegrity/1.0 public-read-only'})
    opener = build_opener(HostRestrictedRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    with opener.open(req, timeout=timeout) as response:
        length = response.headers.get('Content-Length')
        if length and (not length.isascii() or int(length) > MAX_BYTES):
            raise ValueError('declared source size too large')
        buf = response.read(MAX_BYTES + 1)
        if len(buf) > MAX_BYTES:
            raise ValueError('source file too large')
    if not buf.startswith(OLE_MAGIC):
        raise ValueError('not an OLE compound .xls source')
    return buf


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def excel_label(col: int, row: int) -> str:
    name = ''
    col += 1
    while col:
        col, rem = divmod(col - 1, 26)
        name = chr(65 + rem) + name
    return f'{name}{row + 1}'


def inspect_original(data: bytes, source_name: str, *, candidate_limit: int = 350) -> dict:
    if not isinstance(data, bytes) or not data.startswith(OLE_MAGIC) or len(data) > MAX_BYTES:
        raise ValueError('invalid or oversize OLE .xls data')
    import xlrd  # xlrd 2.x parses historical BIFF .xls, without formula execution
    wb = xlrd.open_workbook(file_contents=data, on_demand=True, formatting_info=False)
    sheets = []
    rows_examined = 0
    candidates = []
    for sheet in wb.sheets():
        if rows_examined + sheet.nrows * sheet.ncols > MAX_CELLS:
            raise ValueError('workbook exceeds review cell budget')
        rows_examined += sheet.nrows * sheet.ncols
        sheets.append({'sheet': sheet.name, 'rows': sheet.nrows, 'columns': sheet.ncols})
        for r in range(sheet.nrows):
            for c in range(min(sheet.ncols, 50)):
                v = sheet.cell_value(r, c)
                if not isinstance(v, str) or not PATTERN.search(v):
                    continue
                if len(candidates) >= candidate_limit:
                    break
                around = []
                for cc in range(max(0, c - 2), min(sheet.ncols, c + 8)):
                    val = sheet.cell_value(r, cc)
                    if isinstance(val, (float, int, str, bool)) and val != '':
                        around.append({'cell': excel_label(cc, r), 'value': str(val)[:120]})
                candidates.append({'sheet': sheet.name, 'location': excel_label(c, r), 'label': v[:240], 'same_row': around})
    return {'source_name': source_name, 'file_sha256': sha256(data), 'file_bytes': len(data),
            'workbook_sheets': sheets, 'cells_screened': rows_examined,
            'candidate_rows': candidates, 'candidate_rows_truncated': len(candidates) >= candidate_limit,
            'numerical_metrics_accepted': 0, 'metric_units_confirmed': False,
            'status': 'ORIGINAL_BYTES_PARSED_METRICS_REQUIRE_MANUAL_CELL_MAPPING'}


def run(out: Path, *, require_all: bool = False, save_originals: bool = False) -> tuple[dict, int]:
    out.mkdir(parents=True, exist_ok=True)
    files = out / 'original_xls'
    if save_originals:
        files.mkdir(parents=True, exist_ok=True)
    receipt = {'source_registry': 'https://magadanport.ru/raskrytie-informacii/',
               'scope': 'Magadan Maritime Commercial Port operator financial disclosure forms; not whole-port cargo demand',
               'metrics_accepted': 0, 'period_grain': '9M_CUMULATIVE_NOT_MONTHLY', 'sources': {},
               'company_OD_verified': False, 'new_40ft_paid_volume_verified': False}
    failed = False
    fetched_all = True
    for key, (url, asof) in OFFICIAL.items():
        try:
            content = get_public_xls(url)
        except Exception as exc:
            failed = True
            fetched_all = False
            info = {'source_url': url, 'period_end': asof, 'status': 'SOURCE_NOT_ACQUIRED',
                    'reason': str(exc)[:300], 'raw_file_acquired': False,
                    'file_sha256': None, 'file_bytes': None, 'metrics_accepted': 0}
            receipt['sources'][key] = info
            continue
        # Preserve evidence of the exact original bytes even when the file
        # is encrypted or its BIFF workbook cannot be parsed by xlrd.
        raw_metadata = {'source_url': url, 'period_end': asof,
                        'raw_file_acquired': True, 'ole_compound_confirmed': True,
                        'file_sha256': sha256(content), 'file_bytes': len(content),
                        'metrics_accepted': 0}
        if save_originals:
            (files / (key + '.xls')).write_bytes(content)
        try:
            info = inspect_original(content, key)
            info.update(raw_metadata)
        except Exception as exc:
            failed = True
            info = {**raw_metadata, 'status': 'SOURCE_BYTES_ACQUIRED_PARSING_BLOCKED',
                    'reason': str(exc)[:300], 'candidate_rows': []}
        receipt['sources'][key] = info
    receipt['status'] = ('SOURCE_FETCH_INCOMPLETE' if not fetched_all else
                         'RAW_XLS_ACQUIRED_MAPPING_PENDING' if not failed else
                         'SOURCE_BYTES_ACQUIRED_MAPPING_BLOCKED')
    (out / 'primary_xls_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt, 2 if failed and require_all else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--require-all', action='store_true')
    p.add_argument('--save-originals', action='store_true', help='save only inside transient runner, not git commit')
    p.add_argument('--print-candidates', type=int, default=0, help='print at most N source-labeled candidate cells per report; never accepted figures')
    args = p.parse_args()
    result, code = run(args.output_dir, require_all=args.require_all, save_originals=args.save_originals)
    if args.print_candidates > 0:
        for source_key, details in result['sources'].items():
            print(json.dumps({'source': source_key, 'candidate_only_not_accepted':
                              details.get('candidate_rows', [])[:min(args.print_candidates, 100)]},
                              ensure_ascii=False))
    print(json.dumps({'status': result['status'], 'originals': {
        key: {'sha256': value.get('file_sha256'), 'status': value['status'],
              'raw_file_acquired': value.get('raw_file_acquired', False),
              'file_bytes': value.get('file_bytes'),
              'candidate_rows': len(value.get('candidate_rows', [])),
              'error_if_any': value.get('reason')}
        for key, value in result['sources'].items()},
        'numerical_metrics_accepted': 0, 'company_OD_verified': False}, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
