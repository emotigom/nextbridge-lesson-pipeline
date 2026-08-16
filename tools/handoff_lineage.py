#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

FACTORY_REPOSITORY = 'emotigom/nextbridge-lesson-factory'


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def factory_head(factory_root: Path):
    return subprocess.check_output(['git','-C',str(factory_root),'rev-parse','HEAD'], text=True).strip()


def derive_lineage(handoff_path: Path, factory_root: Path, factory_commit: str, captured_at=None):
    factory_root = factory_root.resolve()
    actual = factory_head(factory_root)
    if actual != factory_commit:
        raise RuntimeError(f'Factory commit mismatch: expected {factory_commit}, got {actual}')
    tool = factory_root / 'tools' / 'lessonctl' / 'handoff.py'
    if not tool.is_file():
        raise RuntimeError('Factory handoff validator missing')
    cp = subprocess.run([sys.executable, str(tool), 'validate', '--file', str(handoff_path.resolve())], text=True, capture_output=True)
    try:
        report = json.loads(cp.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Factory handoff validator returned invalid JSON') from exc
    if cp.returncode != 0 or report.get('status') != 'PASS':
        raise RuntimeError('Factory handoff validation failed: ' + '; '.join(report.get('blockers', [])))
    handoff = json.loads(handoff_path.read_text(encoding='utf-8'))
    sessions = handoff.get('courseMap', {}).get('sessions', [])
    return {
        'schemaVersion':'1.0.0',
        'courseId':report['courseId'],
        'handoffSha256':sha256(handoff_path),
        'designState':report['designState'],
        'sessionCount':len(sessions),
        'approvedSessions':report.get('approvedSessions', []),
        'factoryCommitSha':factory_commit,
        'privateDetailPublished':False,
        'capturedAt':captured_at,
    }


def validate_lineage(record):
    blockers=[]
    if record.get('schemaVersion')!='1.0.0': blockers.append('SCHEMA_VERSION_INVALID')
    if not record.get('courseId'): blockers.append('COURSE_ID_MISSING')
    if len(str(record.get('handoffSha256','')))!=64: blockers.append('HANDOFF_SHA_INVALID')
    if len(str(record.get('factoryCommitSha','')))!=40: blockers.append('FACTORY_SHA_INVALID')
    if record.get('privateDetailPublished') is not False: blockers.append('PRIVATE_DETAIL_MUST_NOT_BE_PUBLISHED')
    count=record.get('sessionCount')
    if not isinstance(count,int) or isinstance(count,bool) or count<1: blockers.append('SESSION_COUNT_INVALID')
    approved=record.get('approvedSessions')
    if not isinstance(approved,list): blockers.append('APPROVED_SESSIONS_INVALID')
    elif approved != list(range(1,len(approved)+1)): blockers.append('APPROVED_SESSIONS_NOT_CONTIGUOUS')
    return sorted(set(blockers))


def main():
    p=argparse.ArgumentParser(prog='handoff_lineage')
    p.add_argument('--handoff', required=True)
    p.add_argument('--factory-root', required=True)
    p.add_argument('--factory-commit', required=True)
    p.add_argument('--captured-at')
    p.add_argument('--out')
    args=p.parse_args()
    try:
        record=derive_lineage(Path(args.handoff),Path(args.factory_root),args.factory_commit,args.captured_at)
        blockers=validate_lineage(record)
        if blockers:
            raise RuntimeError('; '.join(blockers))
        text=json.dumps(record,ensure_ascii=False,indent=2)+'\n'
        if args.out:
            out=Path(args.out)
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(text,encoding='utf-8')
        print(text,end='')
    except (OSError,RuntimeError,json.JSONDecodeError,subprocess.CalledProcessError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False,indent=2),file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__': main()
