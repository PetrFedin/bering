#!/usr/bin/env python3
"""Deterministic malformed-input survival probe; synthetic-only."""
import copy
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.v27_monthly_od_gate import audit_monthly_port, audit_od

rng = random.Random(20261101)
source = [json.loads((ROOT/'data/public/V27_PORT_MONTHLY_UNVERIFIED.json').read_text()),
          json.loads((ROOT/'data/od/V27_GROUP_24M_UNVERIFIED.json').read_text())]
mutants = [None, [], {}, True, False, 0, -1, 1.5, 'NaN', '2026-13',
           ['BAD'], {'spoof':'1'}, '0', 'INVALID']
errors=[]
for i in range(400):
    idx=i%2
    raw=copy.deepcopy(source[idx])
    root=raw
    for _ in range(rng.randint(1,3)):
        current=root
        steps=[]
        for __ in range(rng.randint(1,4)):
            if isinstance(current,dict) and current:
                key=rng.choice(list(current))
                steps.append((current,key))
                current=current[key]
            elif isinstance(current,list) and current:
                key=rng.randrange(len(current))
                steps.append((current,key))
                current=current[key]
            else:
                break
        if steps:
            obj,key=steps[-1]
            obj[key]=rng.choice(mutants)
    try:
        (audit_monthly_port if idx==0 else audit_od)(root)
    except Exception as exc:
        errors.append({'case':i,'kind':type(exc).__name__,'error':str(exc)})
print(json.dumps({'cases':400,'unhandled':len(errors),'examples':errors[:8]},indent=2))
raise SystemExit(1 if errors else 0)
