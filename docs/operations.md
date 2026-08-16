# Pipeline operation notes

실제 교안 상태가 추가되면 다음 순서로 확인합니다.

```bash
python3 tools/pipelinectl.py validate --state courses/<courseId>/state.json
python3 tools/pipelinectl.py status --state courses/<courseId>/state.json
python3 tools/pipelinectl.py wip-check --root courses
```

사람 승인은 `state.json`의 해당 approval record에 reviewer/approvedAt과 함께 기록하고 PR로 검토합니다. 자동화가 사람 승인을 대신 생성하지 않습니다.

다음 milestone을 확인할 때:

```bash
python3 tools/pipelinectl.py check \
  --state courses/<courseId>/state.json \
  --to SESSION_1_APPROVED
```

`ALL_CONTENT_APPROVED` 이후 artifact build를 허용하기 전에는 Factory binding도 함께 확인합니다.

```bash
python3 tools/pipelinectl.py factory-check \
  --state courses/<courseId>/state.json \
  --factory-root ../nextbridge-lesson-factory
```

GitHub Actions의 `Design Promotion Gate`도 같은 검사를 실행합니다.
