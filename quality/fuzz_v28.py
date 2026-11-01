#!/usr/bin/env python3
"""Reproducible 750 synthetic mutations; ensure fail-closed, not market validation."""
import copy
import json
from pathlib import Path
import random
import sys
root=Path(__file__).parents[1]
sys.path.insert(0,str(root))
from scripts.v28_market_perimeter import assess

rng=random.Random(20261102)
original=json.loads((root/'data/public/V28_MAGADAN_MARKET_PERIMETER.json').read_text())
corruptions=[None,True,False,0,1,-1,1.25,[],{},[1],['a'],
             '','nan','NaN','1e9999','999999999999999999',
             'https://[broken-ipv6','https://example.com','2027-01-01']
uncaught=[]
invalid=0
for trial in range(750):
    doc=copy.deepcopy(original)
    for _ in range(rng.randrange(1,5)):
        obj=doc
        last=None
        for _ in range(rng.randrange(1,7)):
            if isinstance(obj,dict) and obj:
                k=rng.choice(list(obj));last=(obj,k);obj=obj[k]
            elif isinstance(obj,list) and obj:
                k=rng.randrange(len(obj));last=(obj,k);obj=obj[k]
            else:
                break
        if last is not None:
            x,k=last;x[k]=rng.choice(corruptions)
    try:
        res=assess(doc)
        if res['bankable_revenue_approved'] or res['investment_approved']:
            uncaught.append((trial,'SECURITY_BYPASS'))
        if res['status']=='INVALID': invalid+=1
    except Exception as ex:
        uncaught.append((trial,type(ex).__name__,str(ex)[:130]))
print(json.dumps({'mutation_cases':750,'invalid_inputs_detected':invalid,
                  'unhandled_or_false_admission':len(uncaught),
                  'examples':uncaught[:15]},indent=2))
if uncaught:raise SystemExit(1)
