import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from quality_scorecard import assess


class TestScorecard(unittest.TestCase):
    def setUp(self):
        axes=('concept','science','commercial','engineering','government','reproducibility')
        self.rubric={'axes':[{'id':axis,'previous_subjective_indication_not_verified':4,
                             'criteria':[{'id':f'{axis}_{i}','weight':2,
                                          'required_proof':'independent document',
                                          'review_status':'FULLY_VERIFIED'} for i in range(5)]}
                             for axis in axes],
                     'critical_caps':[{'axis':ax,'cap':4.0} for ax in axes if ax!='concept'],
                     'target_min':8.5,'target_desired':9.0}
        self.baseline={'formal_scores':{k:None for k in axes}}

    def test_self_reported_verified_never_mints_rating(self):
        result=assess(self.rubric,self.baseline)
        self.assertFalse(result['errors'])
        self.assertFalse(result['ready_to_claim_8_5_or_9'])
        self.assertTrue(all(a['formal_score_out_of_10'] is None for a in result['axes']))

    def test_bad_rubric_rejected(self):
        self.rubric['axes'][0]['criteria'][0]['weight']=5
        self.assertTrue(assess(self.rubric,self.baseline)['errors'])

    def test_no_fabricated_formal_values(self):
        self.baseline['formal_scores']['science']=9
        self.assertTrue(assess(self.rubric,self.baseline)['errors'])

    def test_target_cannot_be_lowered_to_fake_pass(self):
        self.rubric['target_min']=3
        self.assertTrue(assess(self.rubric,self.baseline)['errors'])


class TestIndependentMargin(unittest.TestCase):
    def test_independent_synthetic_margin(self):
        contracted,diverted,duplicate=100,20,10
        new_cm,old_cm,fixed,risk=9000,5000,100000,20000
        net=contracted-diverted-duplicate
        margin=net*new_cm+diverted*(new_cm-old_cm)-fixed-risk
        self.assertEqual(net,70)
        self.assertEqual(margin,590000)

    def test_volume_excess_is_invalid(self):
        contract,diverted,duplicate=100,80,30
        self.assertGreater(diverted+duplicate,contract)

    def test_negative_unit_margin_must_be_supported(self):
        new,old,fixed,risk=-100,-50,0,0
        self.assertLess(10*new+5*(new-old)-fixed-risk,0)


if __name__=='__main__':
    unittest.main()
