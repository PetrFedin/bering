#!/usr/bin/env python3
"""Review public CY-CY list freight rates without pretending they are net CM."""
import argparse
import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

FIELDS = ('dry_40ft_vvo_to_mag','reefer_40ft_vvo_to_mag',
          'dry_40ft_mag_to_vvo','reefer_40ft_mag_to_vvo')


def dmoney(x):
    if not isinstance(x,(str,int)) or isinstance(x,bool):
        raise ValueError('exact RUB text/integer required')
    try:
        val=Decimal(str(x))
    except InvalidOperation as e:
        raise ValueError('invalid amount') from e
    if not val.is_finite() or val<0 or val.as_tuple().exponent < -2:
        raise ValueError('invalid amount precision/negative/nonfinite')
    return val


def evaluate(data):
    err=[]
    if not isinstance(data,dict):
        return {'status':'INVALID','errors':['must be JSON object'],'bankable_revenue_approved':False}
    fields={'schema':'V27_PUBLIC_CY_CY_RATE','origin':'Vladivostok',
            'destination':'Magadan','scope':'CY_CY_SEA_FREIGHT_ONLY',
            'currency':'RUB','tax_basis':'INCL_VAT',
            'carrier_url':'https://kasco.su/schedule_vvo-mag/'}
    for key,val in fields.items():
        if data.get(key)!=val:
            err.append(key+': expected source-defined value')
    for key,expected in [('rate_is_binding_customer_quote',False),
                         ('port_handling_both_ends_included',True),
                         ('demurrage_and_excess_storage_excluded',True)]:
        if data.get(key) is not expected:
            err.append(key+': mismatch')
    rates=data.get('list_rates')
    if not isinstance(rates,dict) or set(rates)!=set(FIELDS):
        err.append('four exact public 40ft tariff keys required')
        rates={}
    nums={}
    for key in FIELDS:
        try:nums[key]=dmoney(rates.get(key))
        except ValueError:err.append('invalid published rate '+key)
    premium_rub, premium_pct=None,None
    if not err:
        dry=nums['dry_40ft_vvo_to_mag']
        reefer=nums['reefer_40ft_vvo_to_mag']
        if dry<=0:
            err.append('positive dry rate required')
        else:
            premium_rub=str(reefer-dry)
            premium_pct=str(((reefer/dry-1)*Decimal('100')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    return {'status':'PUBLIC_LIST_RATE_ONLY' if not err else 'INVALID',
            'source_url':data.get('carrier_url'),
            'quoted_40ft_dry_rub_incl_vat':str(nums.get('dry_40ft_vvo_to_mag')) if not err else None,
            'quoted_40ft_reefer_rub_incl_vat':str(nums.get('reefer_40ft_vvo_to_mag')) if not err else None,
            'reefer_minus_dry_rub_incl_vat':premium_rub if not err else None,
            'reefer_vs_dry_premium_percent':premium_pct if not err else None,
            'gross_to_net_vat_conversion_done':False,
            'sea_freight_handling_included':data.get('port_handling_both_ends_included') is True,
            'd2d_rub':None, 'group_incremental_margin_rub':None,
            'signed_quote_verified':False,'bankable_revenue_approved':False,
            'errors':err}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    result=evaluate(json.loads(a.input.read_text(encoding='utf-8')))
    text=json.dumps(result,indent=2)+'\n'
    print(text,end='')
    if a.out:a.out.write_text(text,encoding='utf-8')
    return 2 if result['status']=='INVALID' else 0


if __name__=='__main__':raise SystemExit(main())
