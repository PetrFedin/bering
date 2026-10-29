#!/usr/bin/env python3
"""Strict, read-only Excel formula-lineage check for one immutable V15.2 release.

Purpose: independently detect formula or cached-output alterations, not calculate
unseen cashflows. Hashes pin the source original; a planned model revision must
receive a new manifest and be independently reviewed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from openpyxl import load_workbook

GATE_SHEET = "63_V14_Допвклад"
D2D_SHEET = "61_V14_D2D_итог"
FINAL_SHEET = "67_V14_Гейты"

def digest_json(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()

def scan(path: Path) -> dict:
    workbook=load_workbook(path, read_only=False, data_only=False)
    cached=load_workbook(path, read_only=True, data_only=True)
    records=[]; missing=[]; embedded_errors=[]; external_links=[]
    for i, sheet in enumerate(workbook.worksheets):
        cv=cached.worksheets[i]
        for row in sheet:
            for cell in row:
                if cell.data_type != 'f':
                    continue
                records.append([sheet.title, cell.coordinate, cell.value])
                value=cv[cell.coordinate].value
                if value is None:
                    missing.append(sheet.title+'!'+cell.coordinate)
                if '#REF!' in cell.value:
                    embedded_errors.append(sheet.title+'!'+cell.coordinate)
                if '[' in cell.value and ']' in cell.value:
                    external_links.append(sheet.title+'!'+cell.coordinate)
    # Cache validity for the real three pilots, separate from arithmetic scenarios.
    gates={}
    for name, col in ((GATE_SHEET,'N'),(D2D_SHEET,'F'),(FINAL_SHEET,'H')):
        gates[name]={f'{col}{r}':cached[name][f'{col}{r}'].value for r in (5,6,7)}
    result={
        'workbook_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'formula_sha256':digest_json(records),
        'formula_count':len(records),
        'sheet_count':len(workbook.worksheets),
        'sheet_names_sha256':digest_json(workbook.sheetnames),
        'missing_caches':len(missing),
        'missing_caches_sha256':digest_json(missing),
        'missing_cache_addresses':missing,
        'embedded_formula_ref_errors':embedded_errors,
        'external_link_formulas':external_links,
        'hidden_sheets':[s.title for s in workbook.worksheets if s.sheet_state!='visible'],
        'pilot_gate_caches':gates,
        'actual_excel_formula_recalculation_performed':False,
    }
    return result

def assess(observation: dict, expected: dict) -> dict:
    checks={}
    for field in ('workbook_sha256','formula_sha256','formula_count','sheet_count',
                  'missing_caches','missing_caches_sha256'):
        checks[field]=observation[field]==expected.get(field)
    checks['sheet_names_sha256']=observation['sheet_names_sha256']==expected.get('sheet_names_sha256')
    checks['no_external_formula_links']=len(observation['external_link_formulas'])==0
    checks['no_ref_formula_errors']=len(observation['embedded_formula_ref_errors'])==0
    checks['no_hidden_sheets']=len(observation['hidden_sheets'])==0
    checks['three_pilots_hold']=(all(v=='HOLD'
        for gate in observation['pilot_gate_caches'].values() for v in gate.values()))
    return {'status':'PASS_FORMULA_LINEAGE_ONLY' if all(checks.values()) else 'FAIL',
            'checks':checks,'observation':observation,
            'fully_recalculated':False,'contracts_verified':False,
            'suitable_for_investment_decision':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--book',type=Path,required=True)
    p.add_argument('--expected',type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    r=assess(scan(a.book),json.loads(a.expected.read_text(encoding='utf-8')))
    if a.out:a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':r['status'],'checks':r['checks'],'formula_count':r['observation']['formula_count']},indent=2))
    return 0 if r['status'].startswith('PASS') else 1

if __name__=='__main__':raise SystemExit(main())
