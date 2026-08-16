#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / 'config' / 'defaults.json'
PROMPT_TEMPLATE = ROOT / 'templates' / 'new-lesson' / 'chatgpt-start.md'
COURSE_ID = re.compile(r'^[a-z0-9][a-z0-9-]{2,63}$')


def pending():
    return {'status':'PENDING','reviewer':None,'approvedAt':None}


def is_within(path: Path, parent: Path):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def build_initial_state(course_id: str, sessions: int, factory_commit: str):
    return {
        'schemaVersion':'1.0.0',
        'courseId':course_id,
        'activeWip':True,
        'sessionCount':sessions,
        'factory':{
            'repository':'emotigom/nextbridge-lesson-factory',
            'commitSha':factory_commit,
            'verificationMode':'HANDOFF_LINEAGE',
            'designRefPath':f'handoffs/{course_id}.json',
        },
        'approvals':{
            'cleanIntake':pending(),
            'courseMap':pending(),
            'sessions':[{'session':i, **pending()} for i in range(1,sessions+1)],
            'allContent':pending(),
            'pptxBuild':pending(),
            'practiceToolBuild':pending(),
        },
    }


def create_workspace(course_id: str, title: str, sessions: int, workspace: Path, factory_commit: str | None = None):
    if not COURSE_ID.fullmatch(course_id):
        raise ValueError('course-id must match ^[a-z0-9][a-z0-9-]{2,63}$')
    if not title.strip():
        raise ValueError('title is required')
    if not 1 <= sessions <= 20:
        raise ValueError('sessions must be between 1 and 20')
    workspace = workspace.resolve()
    if is_within(workspace, ROOT):
        raise ValueError('private workspace must be outside the public Pipeline repository')
    if workspace.exists() and any(workspace.iterdir()):
        raise ValueError('workspace must not already contain files')

    defaults=json.loads(DEFAULTS.read_text(encoding='utf-8'))
    factory_commit=factory_commit or defaults['factoryCommitSha']
    if not re.fullmatch(r'[0-9a-f]{40}', factory_commit):
        raise ValueError('factory commit must be an exact 40-character SHA')

    workspace.mkdir(parents=True, exist_ok=True)
    (workspace/'inputs').mkdir()
    (workspace/'handoff').mkdir()
    (workspace/'pipeline-draft').mkdir()

    prompt=PROMPT_TEMPLATE.read_text(encoding='utf-8')
    prompt=prompt.replace('{{COURSE_ID}}',course_id).replace('{{TITLE}}',title).replace('{{SESSIONS}}',str(sessions))
    (workspace/'00_START_CHATGPT.md').write_text(prompt,encoding='utf-8')

    state=build_initial_state(course_id,sessions,factory_commit)
    (workspace/'pipeline-state.draft.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    metadata={
        'schemaVersion':'1.0.0','courseId':course_id,'title':title,'sessionCount':sessions,
        'factoryRepository':'emotigom/nextbridge-lesson-factory','factoryCommitSha':factory_commit,
        'publicGitReady':False,
    }
    (workspace/'workspace.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (workspace/'inputs'/'README.md').write_text('허용할 원본 자료를 이 폴더에서 관리합니다. public Git에 자동 업로드되지 않습니다.\n',encoding='utf-8')
    (workspace/'handoff'/'README.md').write_text(
        'course map 승인 이후 ChatGPT에서 Factory handoff 요청 템플릿을 사용해 handoff.json을 여기에 저장합니다.\n'
        '전체 콘텐츠 승인 전에도 중간 handoff 검증은 가능하지만 PPTX build 승인은 열리지 않습니다.\n',encoding='utf-8')
    (workspace/'README.md').write_text(
        f'# {title}\n\n1. `00_START_CHATGPT.md`를 새 ChatGPT 교안 대화방에 붙여넣습니다.\n'
        '2. 허용 자료를 `inputs/`에서 관리합니다.\n'
        '3. 승인된 대화 상태를 `handoff/handoff.json`으로 저장합니다.\n'
        '4. Pipeline 저장소의 `tools/handoff_sync.py`로 public-safe 초안을 만듭니다.\n'
        '5. 생성된 state/lineage는 사람이 검토한 뒤 PR로 반영합니다.\n'
        '6. HANDOFF_LINEAGE 상태에서는 PPTX/실습도구 build 승인이 금지됩니다.\n',encoding='utf-8')
    return {'status':'CREATED','workspace':str(workspace),'courseId':course_id,'sessionCount':sessions,'factoryCommitSha':factory_commit}


def main():
    p=argparse.ArgumentParser(prog='new_lesson')
    p.add_argument('--course-id',required=True)
    p.add_argument('--title',required=True)
    p.add_argument('--sessions',type=int,required=True)
    p.add_argument('--workspace',required=True)
    p.add_argument('--factory-commit')
    args=p.parse_args()
    try:
        result=create_workspace(args.course_id,args.title,args.sessions,Path(args.workspace),args.factory_commit)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(json.dumps({'status':'FAIL','error':str(exc)},ensure_ascii=False,indent=2))
        raise SystemExit(2)


if __name__=='__main__': main()
