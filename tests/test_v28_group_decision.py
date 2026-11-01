import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.v28_group_decision import run_gate, INPUTS


class Proc:
    def __init__(self,payload,code=0):
        self.returncode=code
        self.stdout=json.dumps(payload)
        self.stderr=''


def children():
    return [
        {'status':'CONTEXT_VALID_REVIEW_REQUIRED',
         'historical_port_teu':{'physical_40ft_containers':None},
         'project_capacity_version_conflict':{'future_in_service_capacity':None},
         'investment_approved':False,'bankable_revenue_approved':False},
        {'operator_monthly':{'status':'HOLD'},
         'group_24m_od':{'status':'HOLD','projection':None},
         'investment_approved':False,'bankable_revenue_approved':False},
        {'status':'HOLD','source_categories_with_locally_verified_bytes':0,
         'investment_approved':False,'bankable_revenue_approved':False},
        {'status':'HOLD','investment_approved':False,'bankable_revenue_approved':False},
    ]


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for rel in INPUTS.values():
            p=self.root/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('{"fake":"fixture"}\n',encoding='utf-8')

    def runner(self, children_data=None):
        responses=iter([Proc(i) for i in (children_data or children())])
        return lambda *args,**kwargs: next(responses)

    def test_empty_real_source_is_hold(self):
        r=run_gate(self.root,runner=self.runner())
        self.assertEqual(r['status'],'HOLD')
        self.assertEqual(r['component_status']['commercial'],'HOLD')
        self.assertEqual(r['component_status']['group_od'],'HOLD')
        self.assertIsNone(r['incremental_group_cm_rub'])
        self.assertFalse(r['investment_approved'])
        self.assertEqual(len(r['source_sha256']),4)

    def test_missing_source_invalid(self):
        (self.root/INPUTS['v27_od']).unlink()
        self.assertEqual(run_gate(self.root,runner=self.runner())['status'],'INVALID')

    def test_market_invalid_fails(self):
        records=children()
        records[0]['status']='INVALID'
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_market_fake_40ft_invalid(self):
        records=children()
        records[0]['historical_port_teu']['physical_40ft_containers']='500'
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_falsely_claimed_commissioned_capacity_invalid(self):
        records=children()
        records[0]['project_capacity_version_conflict']['future_in_service_capacity']='150000'
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_pilot_paid_baseline_pass_fails(self):
        records=children()
        records[3]['status']='REVIEW'
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_od_fake_projection_fails(self):
        records=children()
        records[1]['group_24m_od']['projection']={'P1':1000}
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_any_fake_bankable_flag_fails(self):
        records=children()
        records[2]['bankable_revenue_approved']=True
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_source_changed_midgate_fails(self):
        responses=iter([Proc(i) for i in children()])
        path=self.root/INPUTS['v27_od']
        def bad_runner(*args,**kwargs):
            path.write_text('{"mutated":true}',encoding='utf-8')
            return next(responses)
        r=run_gate(self.root,runner=bad_runner)
        self.assertEqual(r['status'],'INVALID')
        self.assertIn('Input source bytes changed',str(r['errors']))

    def test_empty_child_response_invalid(self):
        records=children()
        records[0]=[]
        responses=iter([Proc(i) for i in records])
        r=run_gate(self.root,runner=lambda *args,**kw: next(responses))
        self.assertEqual(r['status'],'INVALID')

    def test_malformed_nested_status_never_crashes(self):
        records=children()
        records[0]['historical_port_teu']=None
        records[1]['group_24m_od']=None
        self.assertEqual(run_gate(self.root,runner=self.runner(records))['status'],'INVALID')

    def test_child_error_not_swallowed(self):
        records=iter([Proc(i,code=1 if idx==1 else 0) for idx,i in enumerate(children())])
        r=run_gate(self.root,runner=lambda *args,**kw: next(records))
        self.assertEqual(r['status'],'INVALID')


if __name__=='__main__':
    unittest.main()
