#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from handoff_lineage import derive_lineage, validate_lineage
from pipelinectl import validate_state, derived_milestone

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / 'config' / 'defaults.json'


def pending():
    return {'status':'PENDING','reviewer':None,'approvedAt':None}


def state_from_handoff(handoff: dict, lineage: dict, factory_commit: str):
    approvals=handoff['approvals']
    state={
        'schemaVersion':'1.0.0',
        'courseId':handoff['courseId'],
        'activeWip':True,
        'sessionCount':len(handoff['courseMap']['sessions']),
        'factory':{
            'repository':'emotigom/nextbridge-lesson-factory',
            'commitSha':factory_commit,
            'verificationMode':'HANDOFF_LINEAGE',
            'designRefPath':f'handoffs/{handoff["courseId"]}.json',
        },
        'approvals':{
            'cleanIntake':dict(approvals['cleanIntake']),
            'courseMap':dict(approvals['courseMap']),
            'sessions':[dict(x) for x in approvals['sessions']],
            'allContent':dict(approvals['allContent']),
            'pptxBuild':pending(),
            'practiceToolBuild':pending(),
        },
    }
    blockers=validate_state(state)
    if blockers:
        raise RuntimeError('generated Pipeline state invalid: ' + '; '.join(blockers))
    if derived_milestone(state) != lineage['designState']:
        raise RuntimeError('generated Pipeline milestone does not match handoff lineage')
    return state


def prepare(handoff_path: Path, factory_root: Path, factory_commit: str, out_dir: Path, captured_at=None):
    if out_dir.exists() and any(out_dir.iterdir()):
        raise RuntimeError('output directory must be empty')
    lineage=derive_lineage(handoff_path,factory_root,factory_commit,captured_at)
    blockers=validate_lineage(lineage)
    if blockers:
        raise RuntimeError('lineage invalid: ' + '; '.join(blockers))
    handoff=json.loads(handoff_path.read_text(encoding='utf-8'))
    state=state_from_handoff(handoff,lineage,factory_commit)

    course_id=handoff['courseId']
    lineage_path=out_dir/'handoffs'/f'{course_id}.json'
    state_path=out_dir/'courses'/course_id/'state.json'
    lineage_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.parent.mkdir(parents=True,exist_ok=True)
    lineage_path.write_text(json.dumps(lineage,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary={
        'status':'PREPARED',
        'courseId':course_id,
        'designState':lineage['designState'],
        'handoffSha256':lineage['handoffSha256'],
        'lineagePath':str(lineage_path),
        'statePath':str(state_path),
        'buildApprovals':'PENDING',
        'humanReviewRequired':True,
    }
    (out_dir/'SYNC_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(prog='handoff_sync')
    p.add_argument('--handoff',required=True)
    p.add_argument('--factory-root',required=True)
    p.add_argument('--factory-commit')
    p.add_argument('--out-dir',required=True)
    p.add_argument('--captured-at')
    args=p.parse_args()
    try:
        defaults=json.loads(DEFAULTS.read_text(encoding='utf-8'))
        commit=args.factory_commit or defaults['factoryCommitSha']
        result=prepare(Path(args.handoff),Path(args.factory_root),commit,Path(args.out_dir),args.captured_at)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (OSError,RuntimeError,ValueError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False,indent=2))
        raise SystemExit(2)


if __name__=='__main__': main()
