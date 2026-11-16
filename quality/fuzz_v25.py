"""Deterministic V25 malformed-JSON fuzz runner; synthetic fixtures only.

Run: python quality/fuzz_v25.py. Exit nonzero if any raw schema mutation causes
an uncaught exception instead of the expected INVALID/HOLD/REVIEW outcome.
"""
from pathlib import Path
import random
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'tests'))
sys.path.insert(0, str(root / 'scripts'))
from test_independent_custody_payment_v25 import V25Tests
from independent_custody_payment_v25 import evaluate

rng = random.Random(20261031)
mutations = [None, 0, 1, True, False, '', 'TEST', '2026-09-01',
             [], {}, ['a'], 'NaN', 9999999, 3.14159]
exceptions = []
for case_num in range(800):
    case = V25Tests(methodName='test_01_full_synthetic_review_not_bankable')
    case.setUp()
    try:
        source = rng.choice((case.v23, case.v24, case.v25))
        for _ in range(rng.randint(1, 3)):
            current = source
            route = []
            for _ in range(rng.randint(1, 6)):
                if isinstance(current, dict) and current:
                    key = rng.choice(list(current))
                    route.append((current, key))
                    current = current[key]
                elif isinstance(current, list) and current:
                    key = rng.randrange(len(current))
                    route.append((current, key))
                    current = current[key]
                else:
                    break
            if route:
                parent, key = route[-1]
                parent[key] = rng.choice(mutations)
        evaluate(case.v23, case.raw23, case.v24, case.raw24, case.v25,
                 evidence_index=case.index, evidence_dir=case.root)
    except Exception as ex:
        exceptions.append((case_num, type(ex).__name__, str(ex)))
    finally:
        case.doCleanups()

print('V25 deterministic corruption cases: 800; uncaught exceptions:', len(exceptions))
for occurrence in exceptions[:30]:
    print(*occurrence)
if exceptions:
    raise SystemExit(1)
