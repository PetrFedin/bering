#!/usr/bin/env python3
"""R20: scope-aware recheck of versioned PАО Magadan MP-1 monthly extraction.

Research-only input; a Git CSV of claimed original XLS extraction is NOT the XLS.
All approvals remain false. No annualization, company-valuation or new 40ft claims.
"""
from __future__ import annotations
import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from collections import Counter

EXPECTED_MONTHS = [f"{year}-{m:02d}" for year, n in [(2024,12),(2025,12),(2026,9)] for m in range(1,n+1)]
FIELDS = ('total_cargo_kt','container_cargo_kt','loaded_teu','reefer_teu','empty_teu')
TEU_FIELDS = ('loaded_teu','empty_teu','reefer_teu')
PORT_WIDE_MEDIA_TEU = {'2024':80900,'2025':84300}
SECONDARY_REPORTED_2024_CONTAINER_KT = Decimal('890.1')
ASOP_REPORTED_2025_OPERATOR_KT = Decimal('1834.7')


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise ValueError('invalid or duplicate headers')
        if not {'month',*FIELDS,'source_file','source_sha256'}.issubset(set(reader.fieldnames)):
            # Local smoke fixture may include the numerical columns only; official repo
            # extraction must carry source file and SHA information.
            raise ValueError('missing columns in source-annotated monthly MP-1 extraction')
        rows=list(reader)
    if len(rows)!=33 or [r['month'] for r in rows]!=EXPECTED_MONTHS:
        raise ValueError('month sequence differs from frozen 2024-01..2026-09 source scope')
    results=[]
    for row in rows:
        source=row['source_sha256']
        if len(source)!=64 or any(c not in '0123456789abcdef' for c in source):
            raise ValueError('source SHA256 field malformed')
        if not row['source_file'].endswith('.xls'):
            raise ValueError('unknown source file suffix')
        checked=dict(row)
        for k in FIELDS:
            raw=row[k]
            if raw is None or raw.strip()=='' or ',' in raw:
                raise ValueError(f'missing/noncanonical {k}')
            try:v=Decimal(raw)
            except (InvalidOperation, TypeError):raise ValueError(f'invalid numeric {k}') from None
            if not v.is_finite() or v<0:
                raise ValueError(f'nonfinite/negative {k}')
            if k in TEU_FIELDS and v!=v.to_integral_value():
                raise ValueError(f'fractional TEU {k}')
            checked[k]=v
        if checked['container_cargo_kt']>checked['total_cargo_kt']:
            raise ValueError('container tonnes exceed operator total')
        # Do not enforce reefer<=loaded: MP-1 data dictionary not re-read from originals.
        results.append(checked)
    return results


def D(v):return str(v.quantize(Decimal('0.001')))

def round2(v):return str(v.quantize(Decimal('0.01')))

def pct_delta(a,b):return (b/a - Decimal(1))*Decimal(100)

def aggregate(rows, year, months):
    x=[r for r in rows if r['month'].startswith(str(year)+'-') and int(r['month'][-2:])<=months]
    if len(x)!=months:raise ValueError('incomplete months')
    values={k:sum((r[k] for r in x),Decimal(0)) for k in FIELDS}
    values['loaded_plus_empty_teu']=values['loaded_teu']+values['empty_teu']
    values['empty_share_pct']=values['empty_teu']/values['loaded_plus_empty_teu']*100 if values['loaded_plus_empty_teu'] else None
    values['container_tonnes_per_combined_teu']=(values['container_cargo_kt']*1000/values['loaded_plus_empty_teu']) if values['loaded_plus_empty_teu'] else None
    return values


def assess(rows):
    a=aggregate(rows,'2025',9); b=aggregate(rows,'2026',9)
    fy24=aggregate(rows,'2024',12);fy25=aggregate(rows,'2025',12)
    ytd={}
    for k in ('total_cargo_kt','container_cargo_kt','loaded_teu','empty_teu','loaded_plus_empty_teu','reefer_teu'):
        ytd[k]={"2025_9m":D(a[k]),"2026_9m":D(b[k]),"delta":D(b[k]-a[k]),"yoy_pct":round2(pct_delta(a[k],b[k])) if a[k] else None}
    zero_reefer_months=[r['month'] for r in rows if r['reefer_teu']==0]
    snapshot={
        "status":"RESEARCH_CONTEXT_ONLY",
        "basis":"REPO_MP1_MONTHLY_CSV_EXTRACTION_NOT_RECOMPUTED_FROM_ORIGINAL_XLS",
        "calendar_months":len(rows),"months_2025_9m":9,"months_2026_9m":9,
        "ytd_operator":ytd,
        "empty_share_2025_9m_pct":round2(a['empty_share_pct']),
        "empty_share_2026_9m_pct":round2(b['empty_share_pct']),
        "empty_share_change_pp":round2(b['empty_share_pct']-a['empty_share_pct']),
        "container_tonnes_per_total_teu_2025_9m":round2(a['container_tonnes_per_combined_teu']),
        "container_tonnes_per_total_teu_2026_9m":round2(b['container_tonnes_per_combined_teu']),
        "fy2024_operator_loaded_plus_empty_teu":int(fy24['loaded_plus_empty_teu']),
        "fy2025_operator_loaded_plus_empty_teu":int(fy25['loaded_plus_empty_teu']),
        "fy2024_portwide_secondary_teu":PORT_WIDE_MEDIA_TEU['2024'],
        "fy2025_portwide_secondary_teu":PORT_WIDE_MEDIA_TEU['2025'],
        "fy2024_portwide_minus_operator_teu":PORT_WIDE_MEDIA_TEU['2024']-int(fy24['loaded_plus_empty_teu']),
        "fy2025_portwide_minus_operator_teu":PORT_WIDE_MEDIA_TEU['2025']-int(fy25['loaded_plus_empty_teu']),
        "fy2024_operator_container_kt":D(fy24['container_cargo_kt']),
        "fy2024_secondary_report_container_kt":D(SECONDARY_REPORTED_2024_CONTAINER_KT),
        "fy2024_secondary_minus_operator_container_kt":D(SECONDARY_REPORTED_2024_CONTAINER_KT-fy24['container_cargo_kt']),
        "fy2025_operator_total_cargo_kt":D(fy25['total_cargo_kt']),
        "fy2025_asop_claim_operator_kt":D(ASOP_REPORTED_2025_OPERATOR_KT),
        "fy2025_asop_minus_operator_total_kt":D(ASOP_REPORTED_2025_OPERATOR_KT-fy25['total_cargo_kt']),
        "reefer_zero_months_requiring_source_check":zero_reefer_months,
        "teu_not_additive_to_reefer_teu":True,
        "port_2026_actual_capacity_teu":None,
        "actual_2026_all_port_throughput_teu":None,
        "current_2026_port_utilization_pct":None,
        "new_paid_incremental_40ft":None,
        "bering_group_incremental_cm_rub":None,
        "bering_npv_rub":None,
        "signed_docs_received_in_this_run":0,
        "bankable_revenue_approved":False,
        "investment_approved":False,
        "notes":[
          "MP1 group/period source scope is not the independent Morcenter port-wide file.",
          "Original MP1 XLS downloads were unavailable in this execution; CSV values are checked, not source-authenticated anew.",
          "Reefer column overlap with loaded is unresolved. Never add reefer to loaded+empty.",
          "Empty and loaded TEU are events; not new revenue, 40ft container count, or independent OD shipments.",
          "Identical 2025 whole-port vs operator totals within rounding do not resolve 2024 differences or legal scope.",
          "FESCO rate dated 2026-11-17 is listed but original tariff attachment not read, price unknown.",
          "20/40ft laden/empty, operator/day/berth split and shipper bank evidences still needed."
        ]
    }
    return snapshot


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default='data/public/MMTP_MP1_MONTHLY_SERIES_2024-01_2026-09.csv')
    p.add_argument('--out')
    args=p.parse_args()
    try:out=assess(read_rows(args.input))
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError) as e:
        out={"status":"INVALID","errors":[f'{type(e).__name__}: {e}'],"investment_approved":False,"bankable_revenue_approved":False}
    s=json.dumps(out,indent=2,ensure_ascii=False)+'\n'
    if args.out:Path(args.out).write_text(s,encoding='utf-8')
    print(s,end='')
    return 0 if out['status']=='RESEARCH_CONTEXT_ONLY' else 2

if __name__=='__main__':raise SystemExit(main())
