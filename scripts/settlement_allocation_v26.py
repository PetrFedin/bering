#!/usr/bin/env python3
"""V26 group invoice/bank payment allocation reconciliation (NOT revenue approval).

One invoice may cover many physical containers; one bank payment may pay
many invoices; an invoice may be settled in several independent transactions.
All source-level input is reviewed BYTES only, not bank statement authenticity.
Zero real source records means UNKNOWN cargo, not observed zero demand.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from source_join_v25 import evidence_ok

TOKEN=re.compile(r'^[0-9a-f]{64}$')
ID=re.compile(r'^[A-Z0-9_-]{6,100}$')

class InvalidLedger(ValueError):
    pass


def dec(raw, label, *, allow_zero=False):
    if isinstance(raw, (bool,float)) or not isinstance(raw,(str,int)):
        raise InvalidLedger(f'{label}: exact decimal text/integer required')
    try: x=Decimal(str(raw))
    except InvalidOperation as e:raise InvalidLedger(f'{label}: invalid decimal') from e
    if not x.is_finite() or x.as_tuple().exponent < -2 or (x < 0 if allow_zero else x <= 0):
        raise InvalidLedger(f'{label}: invalid amount/precision/negative')
    return x


def when(value, as_of, name):
    if not isinstance(value,str):raise InvalidLedger(name+': ISO date missing')
    try: d=date.fromisoformat(value)
    except ValueError as ex: raise InvalidLedger(name+': invalid ISO date') from ex
    if d.isoformat()!=value or d>as_of:
        raise InvalidLedger(name+': future/noncanonical document date')
    return d


def audit(payload, evidence=None, source_root=None, v25=None):
    out={'schema_version':'V26','status':'HOLD','errors':[],'missing':[],
         'matched_physical_40ft':None,'invoice_count':None,'bank_transaction_count':None,
         'mechanically_reconciled_gross_rub':None,
         'source_to_v25_physical_match':False,
         'commercial_additionality_verified':False,
         'group_incremental_cm_rub':None,
         'bank_authenticity_verified':False,
         'bankable_revenue_approved':False,'investment_approved':False,
         'note':'Batch invoice and payment matching does not prove bank authenticity, route incrementality, or future demand.'}
    errs,missing=out['errors'],out['missing']
    if not isinstance(payload,dict):out['status']='INVALID';errs.append('invalid payload');return out
    if payload.get('schema_version')!='V26':errs.append('schema version mismatch')
    if payload.get('currency')!='RUB':errs.append('only RUB permitted, no implicit FX')
    if payload.get('amount_basis')!='GROSS_NET_VAT_SEPARATELY':errs.append('invoice NET/GROSS/VAT reconciliation mandatory')
    if payload.get('source_type')!='SETTLED_INVOICE_ALLOCATION_RESEARCH':errs.append('source classification mismatch')
    if payload.get('refunds_declared') is not False:missing.append('credit notes/refunds not individually reconciled')
    group=payload.get('group_id')
    if not isinstance(group,str) or not ID.fullmatch(group):errs.append('missing/bad economic group')
    try:as_of=when(payload['as_of'],date(2100,1,1),'as_of')
    except (KeyError,InvalidLedger) as ex:as_of=date.min;errs.append(str(ex))
    invs=payload.get('invoices');pays=payload.get('payments')
    if not isinstance(invs,list) or not isinstance(pays,list):errs.append('invoice/payment arrays required');invs=[];pays=[]
    if not invs:missing.append('no invoice originals, NOT confirmed zero sales')
    if not pays:missing.append('no bank settlement originals')
    physical=set();invoice_totals={};invoice_evidence=set()
    for i,invoice in enumerate(invs):
        label=f'invoices[{i}]'
        if not isinstance(invoice,dict):errs.append(label+': not object');continue
        ident=invoice.get('invoice_id')
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in invoice_totals:
            errs.append(label+': invalid/repeated invoice id');continue
        try:
            when(invoice.get('invoice_date'),as_of,label)
            gross=dec(invoice.get('gross_rub'),label+'.gross')
            net=dec(invoice.get('net_rub'),label+'.net')
            vat=dec(invoice.get('vat_rub'),label+'.vat',allow_zero=True)
            if net+vat!=gross:raise InvalidLedger(label+': gross != net + VAT')
            allocations=invoice.get('container_allocations')
            if not isinstance(allocations,list) or not allocations:
                raise InvalidLedger(label+': missing physical container allocation rows')
            gn=gv=Decimal(0);ids=set()
            for j,line in enumerate(allocations):
                sub=f'{label}.container_allocations[{j}]'
                if not isinstance(line,dict):raise InvalidLedger(sub+': invalid row')
                key=line.get('physical_consignment_key')
                if not isinstance(key,str) or not TOKEN.fullmatch(key) or key in ids:
                    raise InvalidLedger(sub+': invalid/duplicate physical key within invoice')
                ids.add(key);physical.add(key)
                n=dec(line.get('net_rub'),sub+'.net')
                v=dec(line.get('vat_rub'),sub+'.vat',allow_zero=True)
                g=dec(line.get('gross_rub'),sub+'.gross')
                if n+v!=g:raise InvalidLedger(sub+': gross != net + VAT')
                gn+=n;gv+=v
            if gn!=net or gv!=vat:
                raise InvalidLedger(label+': allocated net/VAT != invoiced net/VAT')
            invoice_totals[ident]=gross
        except InvalidLedger as exc:errs.append(str(exc));continue
        eid=invoice.get('evidence_id')
        if not evidence_ok(eid,evidence,source_root,as_of):
            missing.append(label+': unverified original invoice bytes')
        if eid in invoice_evidence:errs.append(label+': same original invoice evidence reused for another invoice')
        invoice_evidence.add(eid)
    credited={identifier:Decimal(0) for identifier in invoice_totals}
    pay_ids=set();gross_paid=Decimal(0);payment_evidence=set()
    for i,txn in enumerate(pays):
        label=f'payments[{i}]'
        if not isinstance(txn,dict):errs.append(label+': not object');continue
        ident=txn.get('bank_transaction_id')
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in pay_ids:
            errs.append(label+': invalid/duplicate bank transaction ID');continue
        pay_ids.add(ident)
        try:
            when(txn.get('settlement_date'),as_of,label)
            amt=dec(txn.get('gross_settled_rub'),label+'.gross_settled')
            if txn.get('currency')!='RUB':raise InvalidLedger(label+': bank settlement must be RUB')
            allocations=txn.get('invoice_allocations')
            if not isinstance(allocations,list) or not allocations:
                raise InvalidLedger(label+': missing invoice allocations')
            allocated=Decimal(0);ids=set()
            for j,line in enumerate(allocations):
                sub=f'{label}.invoice_allocations[{j}]'
                if not isinstance(line,dict):raise InvalidLedger(sub+': not object')
                key=line.get('invoice_id')
                if key not in invoice_totals or key in ids:
                    raise InvalidLedger(sub+': unknown/duplicate invoice ID in transaction')
                ids.add(key)
                v=dec(line.get('gross_rub'),sub+'.gross')
                credited[key]+=v;allocated+=v
            if allocated!=amt:raise InvalidLedger(label+': allocated bank transfer != actual transfer')
            gross_paid+=amt
        except InvalidLedger as exc:errs.append(str(exc));continue
        eid=txn.get('evidence_id')
        if not evidence_ok(eid,evidence,source_root,as_of):missing.append(label+': bank statement bytes not reviewed')
        if eid in invoice_evidence:errs.append(label+': source classified simultaneously as invoice and payment')
        # Bank statements can contain many different transaction IDs; shared statement
        # evidence is legal. Require unique txn IDs, never double count actual txn sum.
        payment_evidence.add(eid)
    if any(credited[k]>invoice_totals[k] for k in credited):
        errs.append('bank allocations overpay one or more invoices')
    if any(credited[k]<invoice_totals[k] for k in credited):
        missing.append('partial/unpaid invoices; not fully settled physical sample')
    if v25 is None:missing.append('no independently matched V25 physical ledger')
    elif not isinstance(v25,dict) or v25.get('schema_version')!='V25':errs.append('wrong V25 ledger')
    elif v25.get('group_id')!=group or v25.get('as_of')!=payload.get('as_of'):
        errs.append('different as_of or group between V25 and settlement ledger')
    elif not isinstance(v25.get('shipments'),list):errs.append('invalid V25 physical manifest')
    else:
        physical_v25=[r.get('physical_consignment_key') if isinstance(r,dict) else None for r in v25['shipments']]
        if len(set(physical_v25))!=len(physical_v25) or set(physical_v25)!=physical:
            errs.append('invoice physical keys do not equal V25 keys')
        else:out['source_to_v25_physical_match']=True
    if errs:out['status']='INVALID'
    elif missing:out['status']='HOLD'
    elif invoice_totals and physical and pays:
        out.update({'status':'REVIEW_ONLY','matched_physical_40ft':len(physical),
                    'invoice_count':len(invoice_totals),
                    'bank_transaction_count':len(pay_ids),
                    'mechanically_reconciled_gross_rub':str(gross_paid)})
    out['missing']=sorted(set(missing))
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--v25',type=Path)
    ap.add_argument('--evidence-index',type=Path)
    ap.add_argument('--evidence-root',type=Path)
    ap.add_argument('--output',type=Path)
    opts=ap.parse_args()
    if bool(opts.evidence_index)!=bool(opts.evidence_root):ap.error('evidence index/root pair required')
    e=json.loads(opts.evidence_index.read_text(encoding='utf-8')) if opts.evidence_index else None
    v=json.loads(opts.v25.read_text(encoding='utf-8')) if opts.v25 else None
    r=audit(json.loads(opts.input.read_text(encoding='utf-8')),e,opts.evidence_root,v)
    content=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if opts.output:opts.output.write_text(content,encoding='utf-8')
    print(content)
    return 2 if r['status']=='INVALID' else 3 if r['status']=='HOLD' else 0
if __name__=='__main__':raise SystemExit(main())