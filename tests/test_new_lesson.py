import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('new_lesson',ROOT/'tools'/'new_lesson.py')
n=importlib.util.module_from_spec(spec); spec.loader.exec_module(n)
spec2=importlib.util.spec_from_file_location('pipelinectl',ROOT/'tools'/'pipelinectl.py')
p=importlib.util.module_from_spec(spec2); spec2.loader.exec_module(p)


class TestNewLesson(unittest.TestCase):
    def test_workspace_is_created_with_clean_initial_state(self):
        with tempfile.TemporaryDirectory() as td:
            ws=Path(td)/'lesson'
            result=n.create_workspace('new-course','새 교안',3,ws,'5402f691d2c9d127b05d2063682be266645ee273')
            self.assertEqual('CREATED',result['status'])
            self.assertTrue((ws/'00_START_CHATGPT.md').is_file())
            self.assertTrue((ws/'handoff'/'README.md').is_file())
            state=p.load_json(ws/'pipeline-state.draft.json')
            self.assertEqual([],p.validate_state(state))
            self.assertEqual('CLEAN_INTAKE',p.derived_milestone(state))
            self.assertEqual('HANDOFF_LINEAGE',state['factory']['verificationMode'])
            self.assertEqual(3,len(state['approvals']['sessions']))

    def test_workspace_cannot_be_inside_public_repo(self):
        with self.assertRaises(ValueError):
            n.create_workspace('bad-course','Bad',1,ROOT/'tmp-private','5402f691d2c9d127b05d2063682be266645ee273')

    def test_invalid_course_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                n.create_workspace('Bad Course','Bad',1,Path(td)/'lesson','5402f691d2c9d127b05d2063682be266645ee273')


if __name__=='__main__': unittest.main()
