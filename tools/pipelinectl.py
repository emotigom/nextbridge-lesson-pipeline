#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTORY_REPOSITORY = 'emotigom/nextbridge-lesson-factory'
SHA40 = re.compile(r'^[0-9a-f]{40}$')
SESSION_TARGET = re.compile(r'^SESSION_(\d+)_APPROVED$')
APPROVAL_KEYS = ('cleanIntake','courseMap','allContent','pptxBuild','practiceToolBuild')


class PipelineError(RuntimeError):
    pass


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _approved(record):
    return isinstance(record, dict) and record.get('status') == 'APPROVED'


def _approval_metadata_blockers(name, record):
    blockers = []
    if not isinstance(record, dict):
        return [f'APPROVAL_RECORD_INVALID:{name}']
    if record.get('status') not in ('PENDING','APPROVED'):
        blockers.append(f'APPROVAL_STATUS_INVALID:{name}')
        return blockers
    if record.get('status') == 'APPROVED':
        if not record.get('reviewer'):
            blockers.append(f'APPROVAL_REVIEWER_MISSING:{name}')
        if not record.get('approvedAt'):
            blockers.append(f'APPROVAL_TIME_MISSING:{name}')
    return blockers


def validate_state(state):
    blockers = []
    required = ('schemaVersion','courseId','activeWip','sessionCount','factory','approvals')
    for key in required:
        if key not in state:
            blockers.append(f'MISSING:{key}')
    if blockers:
        return blockers
    if state.get('schemaVersion') != '1.0.0':
        blockers.append('SCHEMA_VERSION_UNSUPPORTED')
    if not re.match(r'^[a-z0-9][a-z0-9-]{2,63}$', str(state.get('courseId',''))):
        blockers.append('COURSE_ID_INVALID')
    if not isinstance(state.get('activeWip'), bool):
        blockers.append('ACTIVE_WIP_NOT_BOOLEAN')
    count = state.get('sessionCount')
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20:
        blockers.append('SESSION_COUNT_INVALID')
        return blockers

    factory = state.get('factory', {})
    if factory.get('repository') != FACTORY_REPOSITORY:
        blockers.append('FACTORY_REPOSITORY_NOT_ALLOWED')
    if not SHA40.match(str(factory.get('commitSha',''))):
        blockers.append('FACTORY_COMMIT_NOT_PINNED_SHA')
    bundle = str(factory.get('designBundlePath',''))
    if not bundle or Path(bundle).is_absolute() or '..' in Path(bundle).parts:
        blockers.append('FACTORY_BUNDLE_PATH_UNSAFE')

    approvals = state.get('approvals', {})
    for key in APPROVAL_KEYS:
        blockers.extend(_approval_metadata_blockers(key, approvals.get(key)))
    sessions = approvals.get('sessions')
    if not isinstance(sessions, list):
        blockers.append('SESSION_APPROVALS_NOT_ARRAY')
        return blockers
    if len(sessions) != count:
        blockers.append(f'SESSION_APPROVAL_COUNT_MISMATCH:{len(sessions)}!={count}')
    numbers = [x.get('session') for x in sessions if isinstance(x, dict)]
    if numbers != list(range(1, count + 1)):
        blockers.append('SESSION_APPROVAL_NUMBERS_NOT_CONTIGUOUS')
    for idx, record in enumerate(sessions, 1):
        blockers.extend(_approval_metadata_blockers(f'session{idx}', record))

    clean = _approved(approvals.get('cleanIntake'))
    course_map = _approved(approvals.get('courseMap'))
    approved_flags = [_approved(x) for x in sessions]
    all_content = _approved(approvals.get('allContent'))
    pptx = _approved(approvals.get('pptxBuild'))
    practice = _approved(approvals.get('practiceToolBuild'))

    if course_map and not clean:
        blockers.append('COURSE_MAP_APPROVED_BEFORE_CLEAN_INTAKE')
    if any(approved_flags) and not course_map:
        blockers.append('SESSION_APPROVED_BEFORE_COURSE_MAP')
    seen_pending = False
    for i, approved in enumerate(approved_flags, 1):
        if not approved:
            seen_pending = True
        elif seen_pending:
            blockers.append(f'SESSION_APPROVAL_GAP:SESSION_{i}')
    if all_content and not all(approved_flags):
        blockers.append('ALL_CONTENT_APPROVED_BEFORE_ALL_SESSIONS')
    if pptx and not all_content:
        blockers.append('PPTX_BUILD_ALLOWED_BEFORE_ALL_CONTENT')
    if practice and not pptx:
        blockers.append('PRACTICE_TOOL_BUILD_ALLOWED_BEFORE_PPTX')
    return sorted(set(blockers))


def derived_milestone(state):
    blockers = validate_state(state)
    if blockers:
        raise PipelineError('; '.join(blockers))
    approvals = state['approvals']
    if not _approved(approvals['cleanIntake']):
        return 'CLEAN_INTAKE'
    if not _approved(approvals['courseMap']):
        return 'CLEAN_INTAKE'
    approved_sessions = sum(1 for x in approvals['sessions'] if _approved(x))
    if approved_sessions == 0:
        return 'COURSE_MAP_APPROVED'
    if approved_sessions < state['sessionCount']:
        return f'SESSION_{approved_sessions}_APPROVED'
    if not _approved(approvals['allContent']):
        return f'SESSION_{state["sessionCount"]}_APPROVED'
    if not _approved(approvals['pptxBuild']):
        return 'ALL_CONTENT_APPROVED'
    if not _approved(approvals['practiceToolBuild']):
        return 'PPTX_BUILD_ALLOWED'
    return 'PRACTICE_TOOL_BUILD_ALLOWED'


def gate_blockers(state, target):
    blockers = validate_state(state)
    if blockers:
        return blockers
    a = state['approvals']
    if target == 'CLEAN_INTAKE':
        return [] if _approved(a['cleanIntake']) else ['CLEAN_INTAKE_NOT_APPROVED']
    if target == 'COURSE_MAP_APPROVED':
        return [] if _approved(a['cleanIntake']) and _approved(a['courseMap']) else ['COURSE_MAP_NOT_APPROVED']
    match = SESSION_TARGET.match(target)
    if match:
        n = int(match.group(1))
        if n < 1 or n > state['sessionCount']:
            return ['SESSION_TARGET_OUT_OF_RANGE']
        if not _approved(a['courseMap']):
            return ['COURSE_MAP_NOT_APPROVED']
        if not all(_approved(x) for x in a['sessions'][:n]):
            return [f'SESSION_{n}_NOT_APPROVED_SEQUENTIALLY']
        return []
    if target == 'ALL_CONTENT_APPROVED':
        return [] if _approved(a['allContent']) and all(_approved(x) for x in a['sessions']) else ['ALL_CONTENT_NOT_APPROVED']
    if target == 'PPTX_BUILD_ALLOWED':
        return [] if _approved(a['pptxBuild']) else ['PPTX_BUILD_NOT_ALLOWED']
    if target == 'PRACTICE_TOOL_BUILD_ALLOWED':
        return [] if _approved(a['practiceToolBuild']) else ['PRACTICE_TOOL_BUILD_NOT_ALLOWED']
    return ['UNKNOWN_TARGET']


def wip_check(states_root: Path):
    files = sorted(states_root.glob('*/state.json')) if states_root.is_dir() else []
    active = []
    parse_errors = []
    for path in files:
        try:
            state = load_json(path)
        except Exception as exc:
            parse_errors.append(f'{path}:{exc}')
            continue
        if state.get('activeWip') is True:
            active.append(state.get('courseId'))
    blockers = []
    if parse_errors:
        blockers.append('STATE_PARSE_ERROR')
    if len(active) != 1:
        blockers.append(f'ACTIVE_WIP_COUNT:{len(active)}')
    return {'status':'PASS' if not blockers else 'FAIL','active':active,'files':len(files),'blockers':blockers,'parseErrors':parse_errors}


def factory_check(state, factory_root: Path):
    blockers = validate_state(state)
    detail = {}
    if blockers:
        return {'status':'FAIL','blockers':blockers,'detail':detail}
    factory_root = factory_root.resolve()
    try:
        actual = subprocess.check_output(['git','-C',str(factory_root),'rev-parse','HEAD'], text=True).strip()
    except Exception as exc:
        return {'status':'FAIL','blockers':['FACTORY_GIT_HEAD_UNAVAILABLE'],'detail':{'error':str(exc)}}
    expected = state['factory']['commitSha']
    detail['factoryRepository'] = FACTORY_REPOSITORY
    detail['expectedCommitSha'] = expected
    detail['actualCommitSha'] = actual
    if actual != expected:
        return {'status':'FAIL','blockers':['FACTORY_COMMIT_SHA_MISMATCH'],'detail':detail}
    tool = factory_root / 'tools' / 'lessonctl' / 'content_design.py'
    bundle = factory_root / state['factory']['designBundlePath']
    if not tool.is_file():
        return {'status':'FAIL','blockers':['FACTORY_CONTENT_DESIGN_TOOL_MISSING'],'detail':detail}
    if not bundle.is_dir():
        return {'status':'FAIL','blockers':['FACTORY_DESIGN_BUNDLE_MISSING'],'detail':detail}
    cp = subprocess.run([sys.executable,str(tool),'check','--path',str(bundle)], text=True, capture_output=True)
    detail['factoryExitCode'] = cp.returncode
    try:
        detail['factoryReport'] = json.loads(cp.stdout) if cp.stdout.strip() else None
    except json.JSONDecodeError:
        detail['factoryStdout'] = cp.stdout[-4000:]
    if cp.returncode != 0:
        detail['factoryStderr'] = cp.stderr[-4000:]
        return {'status':'FAIL','blockers':['FACTORY_CONTENT_DESIGN_FAILED'],'detail':detail}
    return {'status':'PASS','blockers':[],'detail':detail}


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(prog='pipelinectl')
    sub = parser.add_subparsers(dest='cmd', required=True)
    for name in ('validate','status'):
        p = sub.add_parser(name)
        p.add_argument('--state', required=True)
    check = sub.add_parser('check')
    check.add_argument('--state', required=True)
    check.add_argument('--to', required=True)
    wip = sub.add_parser('wip-check')
    wip.add_argument('--root', default='courses')
    fc = sub.add_parser('factory-check')
    fc.add_argument('--state', required=True)
    fc.add_argument('--factory-root', required=True)
    args = parser.parse_args()

    try:
        if args.cmd == 'wip-check':
            report = wip_check(ROOT / args.root)
            _print(report)
            raise SystemExit(0 if report['status'] == 'PASS' else 2)
        state = load_json(Path(args.state))
        if args.cmd == 'validate':
            blockers = validate_state(state)
            report = {'status':'PASS' if not blockers else 'FAIL','courseId':state.get('courseId'),'blockers':blockers}
        elif args.cmd == 'status':
            blockers = validate_state(state)
            report = {'status':'PASS' if not blockers else 'FAIL','courseId':state.get('courseId'),'milestone':derived_milestone(state) if not blockers else None,'blockers':blockers}
        elif args.cmd == 'check':
            blockers = gate_blockers(state,args.to)
            report = {'status':'PASS' if not blockers else 'HOLD','courseId':state.get('courseId'),'target':args.to,'milestone':derived_milestone(state) if not validate_state(state) else None,'blockers':blockers}
        elif args.cmd == 'factory-check':
            report = factory_check(state,Path(args.factory_root))
            report['courseId'] = state.get('courseId')
        else:
            raise PipelineError('unknown command')
        _print(report)
        raise SystemExit(0 if report['status'] == 'PASS' else 2)
    except (PipelineError, json.JSONDecodeError, OSError) as exc:
        _print({'status':'FAIL','error':str(exc)})
        raise SystemExit(2)


if __name__ == '__main__':
    main()
