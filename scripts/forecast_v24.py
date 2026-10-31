#!/usr/bin/env python3
"""V24 evidence-gated, one-year seasonal benchmark for Bering P1/P2/P3.

Only independently byte-reviewed monthly actuals may produce a *screening*
forecast. No source data or contract => HOLD and null forecast. Public port
TONNES are not 40ft paid cargo and are never read by this engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path

PILOTS = ('P1', 'P2', 'P3')
MONTH = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
EVIDENCE_ID = re.compile(r'^EV-[A-Z0-9][A-Z0-9_-]{5,}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')


def month_index(text: str) -> int:
    if not isinstance(text, str) or not MONTH.fullmatch(text):
        raise ValueError('Month must be YYYY-MM')
    year, month = map(int, text.split('-'))
    if not 1900 <= year <= 2100:
        raise ValueError('Month year out of supported range')
    return 12 * year + month - 1


def month_name(index: int) -> str:
    return f'{index // 12:04d}-{index % 12 + 1:02d}'


def verified_bytes(identifier, records, directory, cutoff: date) -> bool:
    """Byte / reviewer authentication, NOT evidence of commercial truth."""
    if (not isinstance(identifier, str) or not EVIDENCE_ID.fullmatch(identifier)
            or not isinstance(records, dict) or directory is None):
        return False
    row = records.get(identifier)
    if not isinstance(row, dict) or row.get('status') != 'VERIFIED':
        return False
    rel = row.get('relative_path')
    digest = row.get('sha256')
    submit = row.get('submitted_by')
    review = row.get('reviewed_by')
    if (not isinstance(rel, str) or not rel or '\\' in rel or '\x00' in rel
            or Path(rel).is_absolute() or '..' in Path(rel).parts
            or not isinstance(digest, str) or not SHA256.fullmatch(digest)
            or not isinstance(submit, str) or not submit.strip()
            or not isinstance(review, str) or not review.strip()
            or submit.strip().casefold() == review.strip().casefold()):
        return False
    try:
        audited = date.fromisoformat(row['reviewed_on'])
        if audited > cutoff:
            return False
        base = Path(directory).resolve(strict=True)
        candidate = base / rel
        if candidate.is_symlink():
            return False
        obj = candidate.resolve(strict=True)
        if not obj.is_relative_to(base) or not obj.is_file() or obj.stat().st_size == 0:
            return False
        h = hashlib.sha256()
        with obj.open('rb') as file:
            for part in iter(lambda: file.read(1024 * 1024), b''):
                h.update(part)
        return h.hexdigest() == digest
    except (OSError, KeyError, ValueError, TypeError):
        return False


def forecast_one(rows: list[tuple[int, int]], last_complete: int):
    """Pre-registered seasonal-naive 12-month forecast; no model selection."""
    if len(rows) < 36 or rows[-1][0] != last_complete:
        return None, None, None
    values = [v for _, v in rows]
    training = values[:-12]
    holdout = values[-12:]
    guesses = training[-12:]
    errors = [actual - guess for actual, guess in zip(holdout, guesses)]
    denom = sum(holdout)
    if denom == 0:
        return None, None, 'HOLDOUT_HAS_ZERO_ACTUALS'
    wape = sum(abs(x) for x in errors) / denom
    lo_error, hi_error = min(errors), max(errors)
    forecast = [
        {'month': month_name(last_complete + i + 1),
         'point_40ft': values[-12 + i],
         'stress_low_40ft': max(0, values[-12 + i] + lo_error),
         'stress_high_40ft': max(0, values[-12 + i] + hi_error)}
        for i in range(12)
    ]
    return forecast, {'holdout_12m_wape': round(wape, 6),
                      'holdout_12m_actual_40ft': denom,
                      'holdout_12m_abs_error_40ft': sum(abs(x) for x in errors),
                      'holdout_12m_bias_40ft': sum(errors),
                      'observed_months': len(rows),
                      'backtest_method': 'fixed-seasonal-naive, final 12 months held out'}, None


def evaluate(payload, evidence_records=None, evidence_directory=None) -> dict:
    errors, missing = [], []
    result = {'schema_version': 'V24', 'status': 'HOLD', 'as_of': None,
              'unit': 'paid_new_40ft_containers', 'pilot_forecasts': {},
              'errors': errors, 'missing': missing,
              'group_forecast_40ft': None, 'group_status': 'HOLD_UNTIL_V23_SOURCE_TIEOUT',
              'bankable_revenue_approved': False,
              'investment_approved': False,
              'forecast_claim': 'SCREENING_ONLY_NOT_CONTRACTED_DEMAND'}
    if not isinstance(payload, dict):
        result['status'] = 'INVALID'
        errors.append('Input must be a JSON object')
        return result
    if payload.get('schema_version') != 'V24':
        errors.append('schema_version must equal V24')
    if payload.get('unit') != 'paid_new_40ft_containers':
        errors.append('Only paid NEW 40ft physical containers; never TEU or tonnes')
    raw_as_of = payload.get('as_of')
    try:
        cutoff = date.fromisoformat(raw_as_of)
        if cutoff.isoformat() != raw_as_of:
            raise ValueError('noncanonical date')
    except (ValueError, TypeError):
        errors.append('Invalid as_of ISO date')
        cutoff = date.min
    result['as_of'] = raw_as_of
    # Current month is incomplete regardless of the day on which the run occurs.
    last_complete = 12 * cutoff.year + cutoff.month - 2
    series = payload.get('series')
    if not isinstance(series, list):
        errors.append('series must be a list with exactly three pilots')
        series = []
    ids = [entry.get('pilot_id') if isinstance(entry, dict) else None for entry in series]
    if len(ids) != 3 or set(ids) != set(PILOTS):
        errors.append('series must contain P1, P2 and P3 exactly once')
    evidence_seen = set()
    for pilot in PILOTS:
        matches = [row for row in series if isinstance(row, dict) and row.get('pilot_id') == pilot]
        if len(matches) != 1:
            continue
        obs = matches[0].get('observations')
        if not isinstance(obs, list):
            errors.append(f'{pilot}: observations must be a list')
            continue
        parsed, trusted = [], True
        months = set()
        for idx, row in enumerate(obs):
            key = f'{pilot}[{idx}]'
            if not isinstance(row, dict):
                errors.append(key + ': observation must be an object')
                continue
            try:
                month = month_index(row.get('month'))
                if month >= last_complete + 1:
                    raise ValueError('Partial/future month not permitted')
                if month in months:
                    raise ValueError('Duplicate monthly observation')
                months.add(month)
            except (ValueError, TypeError) as exc:
                errors.append(key + ': ' + str(exc))
                continue
            count = row.get('paid_new_40ft')
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                errors.append(key + ': paid_new_40ft must be nonnegative integer')
                continue
            if row.get('source_type') != 'SETTLED_ACTUAL':
                errors.append(key + ': source_type must be SETTLED_ACTUAL')
                continue
            eid = row.get('evidence_id')
            if not isinstance(eid, str) or not EVIDENCE_ID.fullmatch(eid):
                errors.append(key + ': invalid evidence identifier')
                continue
            if eid.casefold() in evidence_seen:
                errors.append(key + ': duplicate source evidence across months/pilots')
            evidence_seen.add(eid.casefold())
            if not verified_bytes(eid, evidence_records, evidence_directory, cutoff):
                trusted = False
                missing.append(key + ':independently_byte_verified_actual')
            parsed.append((month, count))
        parsed.sort()
        contiguous = all(b[0] == a[0] + 1 for a, b in zip(parsed, parsed[1:]))
        if parsed and not contiguous:
            missing.append(pilot + ':gapped_months')
        if len(parsed) < 36:
            missing.append(pilot + ':minimum_36_full_observed_months')
        if not parsed or parsed[-1][0] != last_complete:
            missing.append(pilot + ':latest_closed_month_missing')
        if not trusted:
            missing.append(pilot + ':unverified_monthly_evidence')
        month_rows = parsed if contiguous and trusted and len(parsed) >= 36 else []
        forecast, backtest, issue = forecast_one(month_rows, last_complete)
        if issue:
            missing.append(pilot + ':' + issue)
        result['pilot_forecasts'][pilot] = {
            'status': 'REVIEW' if forecast else 'HOLD',
            'observed_months': len(parsed),
            'actual_months_byte_verified': len(parsed) if trusted else None,
            'forecast_12m': forecast,
            'backtest': backtest,
            'note': 'Verified bytes do not establish payment, incremental cargo or signatures; requires external substantive review.'
        }
    if errors:
        result['status'] = 'INVALID'
        for p in result['pilot_forecasts'].values():
            p['status'], p['forecast_12m'], p['backtest'] = 'HOLD', None, None
    else:
        if (set(result['pilot_forecasts']) == set(PILOTS) and
                all(x['status'] == 'REVIEW' for x in result['pilot_forecasts'].values())):
            # Separate per-pilot benchmarks are not a source-level V23 consignment join.
            # Do NOT sum them as additional group cargo until the original waybills
            # are reconciled across P1/P3 and all incumbent terminals.
            result['status'] = 'REVIEW'
    result['missing'] = sorted(set(missing))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--evidence-index', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--require-review', action='store_true')
    args = parser.parse_args()
    if bool(args.evidence_index) != bool(args.evidence_dir):
        parser.error('--evidence-index and --evidence-dir must be paired')
    sources = (json.loads(args.evidence_index.read_text(encoding='utf-8'))
               if args.evidence_index else None)
    result = evaluate(json.loads(args.input.read_text(encoding='utf-8')),
                      sources, args.evidence_dir)
    answer = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(answer, encoding='utf-8')
    print(answer)
    return 2 if result['status'] == 'INVALID' else 3 if args.require_review and result['status'] != 'REVIEW' else 0


if __name__ == '__main__':
    raise SystemExit(main())
