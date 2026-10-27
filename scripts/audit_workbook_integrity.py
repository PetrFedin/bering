#!/usr/bin/env python3
"""Read-only XLSX OOXML release QA, including strict preservation of package parts.

This does NOT recalculate Excel formulas. It checks structural invariants and
cached formula results; mathematical validation requires independent tests.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile,BadZipFile

NS={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def source_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):
            h.update(b)
    return h.hexdigest()


def inspect(path):
    with ZipFile(path) as z:
        files={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    book=ET.fromstring(files['xl/workbook.xml'])
    sheet_count=len(book.findall('x:sheets/x:sheet',NS))
    formula_cells=0;missing_caches=0;formula_errors=[]
    for path_name,content in files.items():
        if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',path_name):
            root=ET.fromstring(content)
            for cell in root.findall('.//x:sheetData/x:row/x:c',NS):
                f=cell.find('x:f',NS)
                if f is not None:
                    formula_cells+=1
                    v=cell.find('x:v',NS)
                    if v is None or (v.text is None and cell.attrib.get('t')!='inlineStr'):
                        missing_caches+=1
                    if cell.attrib.get('t')=='e':
                        formula_errors.append(path_name+':'+str(cell.get('r')))
    return {'sha256':source_digest(path),'filename':path.name,
            'sheets':sheet_count,'formulas':formula_cells,
            'missing_formula_caches':missing_caches,
            'cached_formula_errors':formula_errors,'parts':files}


def check_pair(original,candidate,changed_part='xl/worksheets/sheet64.xml'):
    a=inspect(original);b=inspect(candidate)
    base=a.pop('parts');new=b.pop('parts')
    changed=sorted(p for p in (set(base)|set(new)) if base.get(p)!=new.get(p))
    errors=[]
    if changed!=[changed_part]:
        errors.append('Unexpected modified OOXML members: '+str(changed))
    if a['sheets']!=72 or b['sheets']!=72:
        errors.append('Expected 72 original and candidate sheets')
    if b['formulas']-a['formulas']!=3:
        errors.append('Expected exactly three added risk formulas')
    target=ET.fromstring(new[changed_part])
    cells={c.attrib.get('r'):c for c in target.findall('.//x:sheetData/x:row/x:c',NS)}
    for row in (5,6,7):
        p=cells.get('P'+str(row));n=cells.get('N'+str(row))
        if p is None or n is None:
            errors.append(f'Missing P/N result at row {row}');continue
        f=p.find('x:f',NS);nf=n.find('x:f',NS);nv=n.find('x:v',NS)
        if f is None or ('M'+str(row)+'-O'+str(row)) not in (f.text or '').replace(' ',''):
            errors.append(f'P{row} does not subtract risk column O')
        if nf is None or not all(x in (nf.text or '') for x in ['P'+str(row),'REVIEWED','HOLD']):
            errors.append(f'N{row} does not enforce review and risk-adjusted margin')
        if nv is None or nv.text!='HOLD':
            errors.append(f'N{row} cached result is not explicit HOLD')
    return {'original':a,'candidate':b,'changed_members':changed,'errors':errors,
            'recalculation_performed':False,'independent_commercial_verification':False}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--original',required=True,type=Path)
    parser.add_argument('--candidate',required=True,type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    try:
        result=check_pair(args.original,args.candidate)
    except (OSError,ValueError,KeyError,ET.ParseError,BadZipFile) as e:
        print('FILE_ERROR:',str(e));return 1
    data=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.out:args.out.write_text(data,encoding='utf-8')
    print('sheets=%s, formulas=%s, missing caches=%s, changed=%s, errors=%s'%
          (result['candidate']['sheets'],result['candidate']['formulas'],
           result['candidate']['missing_formula_caches'],len(result['changed_members']),len(result['errors'])))
    for e in result['errors']:print('ERROR:',e)
    return 1 if result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
