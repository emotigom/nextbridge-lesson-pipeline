import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipelinectl', ROOT / 'tools' / 'pipelinectl.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

FIXTURE = json.loads((ROOT / 'fixtures' / 'pipeline' / 'pass' / 'state.json').read_text(encoding='utf-8'))


def approval(status='PENDING', reviewer=None, approved_at=None):
    if status == 'APPROVED':
        reviewer = reviewer or 'reviewer'
        approved_at = approved_at or '2026-08-16T00:00:00Z'
    return {'status': status, 'reviewer': reviewer, 'approvedAt': approved_at}


def four_session_state():
    state = copy.deepcopy(FIXTURE)
    state['courseId'] = 'four-session-fixture'
    state['sessionCount'] = 4
    state['approvals']['sessions'] = [
        {'session': i, **approval()} for i in range(1, 5)
    ]
    state['approvals']['allContent'] = approval()
    state['approvals']['pptxBuild'] = approval()
    state['approvals']['practiceToolBuild'] = approval()
    return state


class TestPipelineCtl(unittest.TestCase):
    def test_pinned_fixture_is_valid_and_all_content_approved(self):
        self.assertEqual([], p.validate_state(FIXTURE))
        self.assertEqual('ALL_CONTENT_APPROVED', p.derived_milestone(FIXTURE))
        self.assertEqual([], p.gate_blockers(FIXTURE, 'ALL_CONTENT_APPROVED'))
        self.assertEqual(['PPTX_BUILD_NOT_ALLOWED'], p.gate_blockers(FIXTURE, 'PPTX_BUILD_ALLOWED'))

    def test_four_session_approvals_advance_one_by_one(self):
        state = four_session_state()
        self.assertEqual('COURSE_MAP_APPROVED', p.derived_milestone(state))
        for i in range(1, 5):
            state['approvals']['sessions'][i-1] = {'session': i, **approval('APPROVED')}
            self.assertEqual(f'SESSION_{i}_APPROVED', p.derived_milestone(state))
            self.assertEqual([], p.gate_blockers(state, f'SESSION_{i}_APPROVED'))
        state['approvals']['allContent'] = approval('APPROVED')
        self.assertEqual('ALL_CONTENT_APPROVED', p.derived_milestone(state))
        state['approvals']['pptxBuild'] = approval('APPROVED')
        self.assertEqual('PPTX_BUILD_ALLOWED', p.derived_milestone(state))
        state['approvals']['practiceToolBuild'] = approval('APPROVED')
        self.assertEqual('PRACTICE_TOOL_BUILD_ALLOWED', p.derived_milestone(state))

    def test_session_gap_is_hard_failure(self):
        state = four_session_state()
        state['approvals']['sessions'][0] = {'session': 1, **approval('APPROVED')}
        state['approvals']['sessions'][2] = {'session': 3, **approval('APPROVED')}
        blockers = p.validate_state(state)
        self.assertIn('SESSION_APPROVAL_GAP:SESSION_3', blockers)

    def test_session_cannot_be_approved_before_course_map(self):
        state = four_session_state()
        state['approvals']['courseMap'] = approval()
        state['approvals']['sessions'][0] = {'session': 1, **approval('APPROVED')}
        self.assertIn('SESSION_APPROVED_BEFORE_COURSE_MAP', p.validate_state(state))

    def test_all_content_cannot_skip_pending_session(self):
        state = four_session_state()
        state['approvals']['sessions'][0] = {'session': 1, **approval('APPROVED')}
        state['approvals']['allContent'] = approval('APPROVED')
        self.assertIn('ALL_CONTENT_APPROVED_BEFORE_ALL_SESSIONS', p.validate_state(state))

    def test_pptx_and_practice_build_gates_cannot_be_bypassed(self):
        state = four_session_state()
        state['approvals']['pptxBuild'] = approval('APPROVED')
        self.assertIn('PPTX_BUILD_ALLOWED_BEFORE_ALL_CONTENT', p.validate_state(state))
        state['approvals']['pptxBuild'] = approval()
        state['approvals']['practiceToolBuild'] = approval('APPROVED')
        self.assertIn('PRACTICE_TOOL_BUILD_ALLOWED_BEFORE_PPTX', p.validate_state(state))

    def test_factory_ref_must_be_exact_commit_sha(self):
        state = copy.deepcopy(FIXTURE)
        state['factory']['commitSha'] = 'main'
        self.assertIn('FACTORY_COMMIT_NOT_PINNED_SHA', p.validate_state(state))

    def test_factory_repository_is_fixed_trusted_repo(self):
        state = copy.deepcopy(FIXTURE)
        state['factory']['repository'] = 'example/attacker-controlled-repo'
        self.assertIn('FACTORY_REPOSITORY_NOT_ALLOWED', p.validate_state(state))

    def test_approved_record_requires_human_metadata(self):
        state = copy.deepcopy(FIXTURE)
        state['approvals']['cleanIntake']['reviewer'] = None
        self.assertIn('APPROVAL_REVIEWER_MISSING:cleanIntake', p.validate_state(state))

    def test_wip_check_requires_exactly_one_active_course(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, active in [('a', True), ('b', False)]:
                d = root / name
                d.mkdir()
                s = copy.deepcopy(FIXTURE)
                s['courseId'] = f'{name}-course'
                s['activeWip'] = active
                (d / 'state.json').write_text(json.dumps(s), encoding='utf-8')
            self.assertEqual('PASS', p.wip_check(root)['status'])
            s = copy.deepcopy(FIXTURE)
            s['courseId'] = 'b-course'
            s['activeWip'] = True
            (root / 'b' / 'state.json').write_text(json.dumps(s), encoding='utf-8')
            report = p.wip_check(root)
            self.assertEqual('FAIL', report['status'])
            self.assertIn('ACTIVE_WIP_COUNT:2', report['blockers'])

    def test_contract_json_is_valid(self):
        json.loads((ROOT / 'contracts' / 'pipeline-state.schema.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
