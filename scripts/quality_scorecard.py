#!/usr/bin/env python3
"""Conservative Bering quality gate: inventory, not a self-awarded grade.

Changing rubric review_status to VERIFIED must never create a 9/10 score.
External specialist assessment and authenticated signoff happen outside this tool.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

AXES = {'concept','science','commercial','engineering','government','reproducibility'}
STAGES = {'NO_EVIDENCE':0.0,'PRELIMINARY':0.25,'PARTIAL_VERIFIED':0.5,
          'MOSTLY_VERIFIED':0.75,'FULLY_VERIFIED':1.0}


def assess(rubric: dict, baseline: dict) -> dict:
    problems=[]; axes=[]; ids=set()
    groups=rubric.get('axes',[])
    if len(groups)!=6 or {a.get('id') for a in groups}!=AXES:
        problems.append('Exactly six distinct named assessment axes required')
    for axis in groups:
        axis_id=axis.get('id')
        criteria=axis.get('criteria',[])
        if len(criteria)!=5:
            problems.append(f'{axis_id}: expected exactly five criteria')
        if sum(c.get('weight',0) for c in criteria)!=10:
            problems.append(f'{axis_id}: weights must add to 10')
        for c in criteria:
            k=c.get('id')
            if not isinstance(k,str) or k in ids:
                problems.append(f'Duplicate/invalid criterion: {k}')
            ids.add(k)
            if not c.get('required_proof'):
                problems.append(f'{k}: no evidence definition')
        caps=[c for c in rubric.get('critical_caps',[]) if c.get('axis')==axis_id]
        if axis_id!='concept' and not caps:
            problems.append(f'{axis_id}: no critical cap')
        axes.append({'axis':axis_id,
                     'previous_subjective_estimate_not_formal':axis.get('previous_subjective_indication_not_verified'),
                     'criteria_total':len(criteria),'criteria_independently_reviewed':0,
                     'formal_score_out_of_10':None,
                     'target_8_5_to_9_status':'NOT_ESTABLISHED',
                     'critical_cap_if_unmet':min([c['cap'] for c in caps],default=None),
                     'requirements':[{'id':c['id'],'proof':c['required_proof'],
                                      'status':'AWAITING_INDEPENDENT_VERIFICATION'} for c in criteria]})
    if len(ids)!=30:
        problems.append(f'Expected 30 unique criteria; found {len(ids)}')
    old=baseline.get('formal_scores',{})
    if any(old.get(k) is not None for k in AXES):
        problems.append('Baseline formal score is non-null without an external review record')
    if rubric.get('target_min')!=8.5 or rubric.get('target_desired')!=9:
        problems.append('Expected proposed threshold 8.5–9.0')
    return {'project':'Bering Corridor',
            'source_rubric':rubric.get('version'),
            'review_standard':'INTERNAL FRAMEWORK, NOT OFFICIAL CERTIFICATION',
            'assessment':'NOT FORMALLY SCORED',
            'independent_reviews_accepted':0,
            'criteria_count':len(ids),
            'axes':axes,'errors':problems,
            'ready_to_claim_8_5_or_9':False,
            'no_averaging_across_axes':True}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--rubric',required=True,type=Path)
    ap.add_argument('--baseline',required=True,type=Path)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    rubric=json.loads(args.rubric.read_text(encoding='utf-8'))
    baseline=json.loads(args.baseline.read_text(encoding='utf-8'))
    result=assess(rubric,baseline)
    content=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(content,encoding='utf-8')
    print('quality axes=%s criteria=%s errors=%s rating=%s'%
          (len(result['axes']),result['criteria_count'],len(result['errors']),result['assessment']))
    for error in result['errors']:
        print('ERROR:',error)
    return 1 if result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
