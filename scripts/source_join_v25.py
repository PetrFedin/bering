#!/usr/bin/env python3
"""V25: exact consignment-level reconciliation of P1/P2/P3 and incumbent terminals.

Original waybills, invoice/payment and group-baseline review are mandatory.
Tokens are pseudonyms from an externally reviewed, confidential source crosswalk.
Passing this software is neither verified commercial demand nor investment approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

PILOTS=('P1','P2','P3')
LEGS={'P1':{'VVO_MAG'},'P2':{'VVO_MAG'},'P3':{'CHINA_VVO','VVO_MAG'}}
TOKEN=re.compile(r'^[0-9a-f]{64}$')
ID=re.compile(r'^[A-Z0-9_-]{6,100}$')
EVID=re.compile(r'^EV-[A-Z0-9_-]{6,100}$')


def money(x):
    if isinstance(x,(float,bool)) or not isinstance(x,(str,int)):
        raise ValueError('money must be exact integer or decimal string')
    try: v=Decimal(str(x))
    except InvalidOperation as exc:raise ValueError('bad decimal') from exc
    if not v.is_finite() or v.as_tuple().exponent < -2:
        raise ValueError('nonfinite or precision beyond 0.01 RUB')
    return v


def evidence_ok(eid, records, root, cutoff):
    if (not isinstance(eid,str) or not EVID.fullmatch(eid)
            or not isinstance(records,dict) or root is None):return False
    doc=records.get(eid)
    if not isinstance(doc,dict) or doc.get('status')!='REVIEWED_BYTES':return False
    rel, expected=doc.get('path'),doc.get('sha256')
    sub, rev=doc.get('submitter'),doc.get('reviewer')
    if (not isinstance(rel,str) or not rel or '\\' in rel or '\x00' in rel
            or '..' in Path(rel).parts or Path(rel).is_absolute()
            or not isinstance(expected,str) or not TOKEN.fullmatch(expected)
            or not isinstance(sub,str) or not sub.strip()
            or not isinstance(rev,str) or not rev.strip()
            or sub.strip().casefold()==rev.strip().casefold()):return False
    try:
        reviewed=date.fromisoformat(doc['reviewed_date'])
        if reviewed>cutoff:return False
        base=Path(root).resolve(strict=True)
        candidate=base/rel
        if candidate.is_symlink():return False
        file=candidate.resolve(strict=True)
        if not file.is_relative_to(base) or not file.is_file() or file.stat().st_size==0:return False
        return hashlib.sha256(file.read_bytes()).hexdigest()==expected
    except (ValueError,TypeError,KeyError,OSError):return False


def verify_v23(join_rows, payload, costs):
    """Compare the SAME physical token/class/margin (not just numeric totals)."""
    if not isinstance(payload,dict) or payload.get('schema_version')!='V23':
        return False,'missing or invalid V23 record'
    if payload.get('currency')!='RUB' or payload.get('tax_basis')!='EX_VAT':
        return False,'V23 tax/currency mismatch'
    v23=payload.get('shipments')
    if not isinstance(v23,list):return False,'V23 shipments absent'
    indexed={}
    for row in v23:
        if not isinstance(row,dict):return False,'bad V23 shipment'
        if row.get('classification')=='EXCLUDED':continue
        key=row.get('physical_consignment_key')
        if not isinstance(key,str) or key in indexed:return False,'duplicate or absent V23 consignment key'
        indexed[key]=row
    if set(indexed)!=set(join_rows):return False,'source-to-source physical identities differ'
    try:
        for key, source in join_rows.items():
            old=indexed[key]
            if (old.get('pilot_id')!=source['pilot_id'] or old.get('economic_shipment_id')!=source['economic_shipment_id']
                or old.get('classification')!=source['classification'] or old.get('quantity_40ft')!=1
                or money(old.get('new_unit_cm_rub'))!=money(source['new_unit_cm_rub'])):
                return False,'V23 consignment economics/route mismatch: '+key
            if source['classification']=='DIVERTED':
                if (money(old.get('incumbent_group_unit_cm_rub'))!=money(source['incumbent_group_unit_cm_rub'])
                        or old.get('incumbent_group_service')!=source['incumbent_group_service']):
                    return False,'V23 incumbent margin mismatch: '+key
            elif old.get('incumbent_group_unit_cm_rub') is not None:
                return False,'V23 false incumbent margin for NEW'
        vcost=payload.get('pilot_costs')
        if not isinstance(vcost,dict) or set(vcost)!=set(PILOTS):return False,'missing V23 pilot costs'
        for p in PILOTS:
            if (money(vcost[p].get('incremental_fixed_rub')) != money(costs[p]['incremental_fixed_rub'])
                    or money(vcost[p].get('incremental_risk_rub')) != money(costs[p]['incremental_risk_rub'])
                    or vcost[p].get('cost_event_ids')!=costs[p].get('cost_event_ids')):
                return False,'V23 cost reconciliation mismatch for '+p
    except (ValueError,KeyError,TypeError) as exc:return False,str(exc)
    return True,None


def audit(payload, records=None, root=None, v23=None):
    out={'schema_version':'V25','status':'HOLD','source_records':0,
         'unique_paid_40ft':None,'group_incremental_cm_rub':None,
         'pilot_incremental_cm_rub':{p:None for p in PILOTS},
         'source_to_v23_match':False,'errors':[],'missing':[],
         'bankable_revenue_approved':False,'investment_approved':False,
         'contractual_demand_verified':False,
         'note':'Pseudonym link + reviewed bytes do not authenticate invoices, signatures, bank settlement or true additionality'}
    err,missing=out['errors'],out['missing']
    if not isinstance(payload,dict):return {**out,'status':'INVALID','errors':['Not a JSON object']}
    if payload.get('schema_version')!='V25':err.append('schema_version must be V25')
    if payload.get('currency')!='RUB' or payload.get('tax_basis')!='EX_VAT':err.append('RUB ex-VAT only')
    try:cutoff=date.fromisoformat(payload['as_of'])
    except (ValueError,TypeError,KeyError):cutoff=date.min;err.append('bad as_of')
    if not isinstance(payload.get('group_id'),str) or not ID.fullmatch(payload.get('group_id','')):
        err.append('missing group_id')
    source=payload.get('shipments')
    legs=payload.get('legs')
    incumbent=payload.get('incumbent_services')
    costs=payload.get('pilot_costs')
    baseline=payload.get('group_baseline')
    if not isinstance(source,list):err.append('shipments must be a list');source=[]
    if not isinstance(legs,list):err.append('legs must be a list');legs=[]
    if not isinstance(incumbent,list):err.append('incumbent_services must be a list');incumbent=[]
    if not isinstance(costs,dict) or set(costs)!=set(PILOTS):err.append('three pilot cost ledgers required');costs={}
    if not isinstance(baseline,dict):err.append('group_baseline object required');baseline={}
    out['source_records']=len(source)
    if not source:missing.append('no physical paid shipments; unknown, NOT observed zero demand')
    if baseline.get('months_covered')!=24:missing.append('independent 24-month group OD baseline incomplete')
    if not evidence_ok(baseline.get('evidence_id'),records,root,cutoff):missing.append('missing reviewed 24-month baseline bytes')
    ids=set(); economic=set(); indexed={}; referenced=set(); ledger={}
    for i,r in enumerate(source):
        label=f'shipments[{i}]'
        if not isinstance(r,dict):err.append(label+':not object');continue
        pilot=r.get('pilot_id');key=r.get('physical_consignment_key');econ=r.get('economic_shipment_id')
        if pilot not in PILOTS:err.append(label+':invalid pilot');continue
        if not isinstance(key,str) or not TOKEN.fullmatch(key):err.append(label+':unverified physical key syntax');continue
        if key in ids:err.append(label+':same physical consignment claimed twice');continue
        ids.add(key)
        if not isinstance(econ,str) or not ID.fullmatch(econ) or econ in economic:
            err.append(label+':duplicate/bad economic ID');continue
        economic.add(econ)
        if r.get('classification') not in ('NEW','DIVERTED'):
            err.append(label+':unknown NEW/DIVERTED classification');continue
        if r.get('quantity_40ft')!=1 or isinstance(r.get('quantity_40ft'),bool):
            err.append(label+':manifest requires one unique physical 40ft per row');continue
        if r.get('currency')!='RUB' or r.get('tax_basis')!='EX_VAT':
            err.append(label+':currency/tax mismatch');continue
        try:
            new=money(r.get('new_unit_cm_rub'))
            if r['classification']=='NEW':
                if r.get('incumbent_group_unit_cm_rub') is not None or r.get('incumbent_group_service') is not None:
                    raise ValueError('NEW cannot have incumbent CM')
                delta=new
            else:
                old=money(r.get('incumbent_group_unit_cm_rub'))
                if not isinstance(r.get('incumbent_group_service'),str) or not r['incumbent_group_service'].strip():
                    raise ValueError('incumbent service identifier missing')
                delta=new-old
        except ValueError as exc:err.append(label+':'+str(exc));continue
        indexed[key]=r
        ledger[key]=delta
        for doc in ('identity','waybill','invoice','payment','unit_cm','additionality'):
            evid=r.get('evidence',{}).get(doc) if isinstance(r.get('evidence'),dict) else None
            if not evidence_ok(evid,records,root,cutoff):missing.append(label+':unverified:'+doc)
            if isinstance(evid,str):
                if evid in referenced:err.append(label+':reused evidence doc ID '+evid)
                referenced.add(evid)
    covered_leg=set();events=set();per_cargo=Counter()
    for i,m in enumerate(legs):
        label=f'legs[{i}]'
        if not isinstance(m,dict):err.append(label+':not object');continue
        key,pilot,route=m.get('physical_consignment_key'),m.get('pilot_id'),m.get('route_leg')
        event=m.get('service_event_id')
        if key not in indexed:err.append(label+':orphan leg/no paid shipment');continue
        if pilot!=indexed[key]['pilot_id'] or route not in LEGS[pilot]:
            err.append(label+':cross-pilot leg mismatch');continue
        if not isinstance(event,str) or not ID.fullmatch(event) or event in events:
            err.append(label+':duplicated/invalid terminal event');continue
        events.add(event)
        if (key,route) in covered_leg:err.append(label+':duplicate leg for physical container')
        covered_leg.add((key,route));per_cargo[key]+=1
        ev=m.get('waybill_evidence_id')
        if not evidence_ok(ev,records,root,cutoff):missing.append(label+':unverified leg document')
    for key,r in indexed.items():
        if {part for token,part in covered_leg if token==key} != LEGS[r['pilot_id']]:
            missing.append('route legs missing for '+key)
    old_seen=set();old_values={}
    for i,z in enumerate(incumbent):
        label=f'incumbent_services[{i}]'
        if not isinstance(z,dict):err.append(label+':not object');continue
        key=z.get('physical_consignment_key')
        if not isinstance(key,str) or not TOKEN.fullmatch(key) or key in old_seen:
            err.append(label+':duplicate/bad incumbent physical identity');continue
        old_seen.add(key)
        if key not in indexed or indexed[key]['classification']!='DIVERTED':
            err.append(label+':incumbent cargo not tagged DIVERTED');continue
        try:
            old=money(z.get('incumbent_group_unit_cm_rub'))
            if (old!=money(indexed[key].get('incumbent_group_unit_cm_rub'))
                    or z.get('incumbent_group_service')!=indexed[key].get('incumbent_group_service')):
                err.append(label+':lost incumbent group earnings not fully reconciled')
            else:old_values[key]=old
        except ValueError as exc:err.append(label+':'+str(exc))
        if not evidence_ok(z.get('old_margin_evidence_id'),records,root,cutoff):
            missing.append(label+':unverified displaced CM source')
    for key,r in indexed.items():
        if r['classification']=='DIVERTED' and key not in old_values:
            missing.append('missing incumbent ledger for diverted cargo '+key)
    valid_costs={}
    cost_events=set()
    for p in PILOTS:
        r=costs.get(p)
        if not isinstance(r,dict):err.append(p+':missing costs');continue
        if not isinstance(r.get('evidence'),dict):err.append(p+':cost evidence must be object');continue
        try:
            fixed=money(r.get('incremental_fixed_rub'));risk=money(r.get('incremental_risk_rub'))
            if fixed<0 or risk<0:raise ValueError('incremental costs must be nonnegative')
            valid_costs[p]=(fixed,risk)
        except ValueError as exc:err.append(p+':'+str(exc))
        cids=r.get('cost_event_ids')
        if not isinstance(cids,dict) or set(cids)!={'fixed','risk'}:
            err.append(p+':two cost events required');continue
        for kind in ('fixed','risk'):
            cid=cids.get(kind)
            if not isinstance(cid,str) or not ID.fullmatch(cid) or cid in cost_events:
                err.append(p+':reused/missing cost event')
            cost_events.add(cid)
            if not evidence_ok(r.get('evidence',{}).get(kind),records,root,cutoff):
                missing.append(p+':unverified '+kind+' cost')
    if v23 is None:missing.append('V23 source-level tie-out not supplied')
    else:
        yes,why=verify_v23(indexed,v23,costs)
        out['source_to_v23_match']=yes
        if not yes:err.append('V23 source mismatch: '+why)
    if err:out['status']='INVALID'
    elif missing:out['status']='HOLD'
    elif indexed and len(valid_costs)==3:
        by_pilot={p:sum((v for k,v in ledger.items() if indexed[k]['pilot_id']==p),Decimal(0))
                  -valid_costs[p][0]-valid_costs[p][1] for p in PILOTS}
        out['pilot_incremental_cm_rub']={p:str(by_pilot[p]) for p in PILOTS}
        total=sum(by_pilot.values(),Decimal(0))
        out['group_incremental_cm_rub']=str(total)
        out['unique_paid_40ft']=len(indexed)
        out['status']='REVIEW_ONLY' if all(x>0 for x in by_pilot.values()) else 'HOLD'
    out['missing']=sorted(set(missing))
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--evidence-index',type=Path)
    parser.add_argument('--evidence-root',type=Path)
    parser.add_argument('--v23',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if bool(args.evidence_index)!=bool(args.evidence_root):parser.error('evidence-index/root are paired')
    records=json.loads(args.evidence_index.read_text(encoding='utf-8')) if args.evidence_index else None
    previous=json.loads(args.v23.read_text(encoding='utf-8')) if args.v23 else None
    result=audit(json.loads(args.input.read_text(encoding='utf-8')),records,args.evidence_root,previous)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text)
    return 2 if result['status']=='INVALID' else 3 if result['status']=='HOLD' else 0
if __name__=='__main__':raise SystemExit(main())
