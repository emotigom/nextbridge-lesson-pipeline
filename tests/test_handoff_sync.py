import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('handoff_sync',ROOT/'tools'/'handoff_sync.py')
h=importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
spec2=importlib.util.spec_from_file_location('pipelinectl',ROOT/'tools'/'pipelinectl.py')
p=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(p)


def approved(at):
    return {'status':'APPROVED','reviewer':'reviewer','approvedAt':at}


class TestHandoffSync(unittest.TestCase):
    def test_all_content_handoff_still_keeps_build_gates_pending(self):
        handoff={
            'courseId':'sync-course',
            'courseMap':{'sessions':[{'session':1}]},
            'approvals':{
                'cleanIntake':approved('2026-08-16T00:00:00Z'),
                'courseMap':approved('2026-08-16T00:01:00Z'),
                'sessions':[{'session':1,**approved('2026-08-16T00:02:00Z')}],
                'allContent':approved('2026-08-16T00:03:00Z'),
            },
        }
        lineage={'designState':'ALL_CONTENT_APPROVED'}
        state=h.state_from_handoff(handoff,lineage,'5402f691d2c9d127b05d2063682be266645ee273')
        self.assertEqual([],p.validate_state(state))
        self.assertEqual('ALL_CONTENT_APPROVED',p.derived_milestone(state))
        self.assertEqual('PENDING',state['approvals']['pptxBuild']['status'])
        self.assertEqual('PENDING',state['approvals']['practiceToolBuild']['status'])
        self.assertEqual(['MATERIALIZED_DESIGN_REQUIRED_BEFORE_PPTX'],p.gate_blockers(state,'PPTX_BUILD_ALLOWED'))

    def test_handoff_lineage_mode_rejects_candidate_or_build_approval(self):
        handoff={
            'courseId':'sync-course',
            'courseMap':{'sessions':[{'session':1}]},
            'approvals':{
                'cleanIntake':approved('2026-08-16T00:00:00Z'),
                'courseMap':approved('2026-08-16T00:01:00Z'),
                'sessions':[{'session':1,**approved('2026-08-16T00:02:00Z')}],
                'allContent':approved('2026-08-16T00:03:00Z'),
            },
        }
        state=h.state_from_handoff(handoff,{'designState':'ALL_CONTENT_APPROVED'},'5402f691d2c9d127b05d2063682be266645ee273')
        state['candidate']={
            'designVersion':'x','qualityOverall':100,
            'packageSha256':'0'*64,'presentationSha256':'0'*64,
            'practiceToolSha256':'0'*64,'activityPackSha256':'0'*64,
        }
        state['approvals']['pptxBuild']=approved('2026-08-16T00:04:00Z')
        blockers=p.validate_state(state)
        self.assertIn('HANDOFF_LINEAGE_CANNOT_HAVE_CANDIDATE',blockers)
        self.assertIn('HANDOFF_LINEAGE_CANNOT_APPROVE_BUILD',blockers)


if __name__=='__main__': unittest.main()
