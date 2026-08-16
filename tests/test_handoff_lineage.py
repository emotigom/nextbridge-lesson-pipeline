import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('handoff_lineage',ROOT/'tools'/'handoff_lineage.py')
h=importlib.util.module_from_spec(spec); spec.loader.exec_module(h)


class TestHandoffLineage(unittest.TestCase):
    def record(self):
        return {
            'schemaVersion':'1.0.0',
            'courseId':'synthetic-course',
            'handoffSha256':'a'*64,
            'designState':'SESSION_1_APPROVED',
            'sessionCount':4,
            'approvedSessions':[1],
            'factoryCommitSha':'b'*40,
            'privateDetailPublished':False,
            'capturedAt':'2026-08-16T22:00:00+09:00',
        }

    def test_public_lineage_shape_passes(self):
        self.assertEqual([],h.validate_lineage(self.record()))

    def test_private_detail_cannot_be_published(self):
        r=self.record(); r['privateDetailPublished']=True
        self.assertIn('PRIVATE_DETAIL_MUST_NOT_BE_PUBLISHED',h.validate_lineage(r))

    def test_approved_sessions_must_be_contiguous(self):
        r=self.record(); r['approvedSessions']=[1,3]
        self.assertIn('APPROVED_SESSIONS_NOT_CONTIGUOUS',h.validate_lineage(r))

    def test_sha256_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'x.json'; p.write_bytes(b'abc')
            self.assertEqual('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',h.sha256(p))

    def test_contract_json_is_valid(self):
        json.loads((ROOT/'contracts'/'handoff-lineage.schema.json').read_text(encoding='utf-8'))


if __name__=='__main__': unittest.main()
