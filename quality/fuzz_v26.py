#!/usr/bin/env python3
"""Deterministic 1,000-case negative input test; no external source files.

Input mutation is not a substitute for human source verification. Fails when
an input reaches a crash instead of a fail-closed status.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from evidence_readiness_v26 import evaluate as intake_audit
from public_market_forecast_v26 import evaluate as market_audit

registry = json.loads((ROOT/'data/public/V26_PUBLIC_SOURCE_REGISTER.json').read_text())
intake = json.loads((ROOT/'data/pilots/V26_EMPTY_PROOF_INTAKE.json').read_text())
rng = random.Random(20261031)
mutations = [None, 0, 1, 3.14159, True, False, '', 'fake', '2099-01-01',
             [], {}, ['bad'], {'id': []}, '1e99999999999']
exceptions = []
for i in range(1000):
    target = copy.deepcopy(registry if i % 2 == 0 else intake)
    for _ in range(rng.randint(1,4)):
        value = target
        selectors = []
        for _ in range(rng.randint(1,6)):
            if isinstance(value, dict) and value:
                key = rng.choice(list(value))
                selectors.append((value, key))
                value = value[key]
            elif isinstance(value, list) and value:
                key = rng.randrange(len(value))
                selectors.append((value, key))
                value = value[key]
            else:
                break
        if selectors:
            parent, key = selectors[-1]
            parent[key] = rng.choice(mutations)
    try:
        result = market_audit(target) if i % 2 == 0 else intake_audit(target)
        if not isinstance(result, dict) or result.get('status') not in (
            'INVALID', 'HOLD', 'PUBLIC_CONTEXT_ONLY', 'READY_FOR_MANUAL_EXTERNAL_AUTHENTICITY_REVIEW'):
            exceptions.append((i, 'NON_CONTRACT_RESULT'))
    except Exception as exc:
        exceptions.append((i, type(exc).__name__, str(exc)[:200]))
print('V26 deterministic mutated inputs:', 1000, 'unhandled errors:', len(exceptions))
for e in exceptions[:20]:
    print(e)
if exceptions:
    raise SystemExit(1)
