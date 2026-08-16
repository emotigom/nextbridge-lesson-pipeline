# Nextbridge Lesson Pipeline

`nextbridge-lesson-pipeline`은 교안 내용을 생성하거나 품질 기준을 정의하는 저장소가 아닙니다.

- **Factory** (`emotigom/nextbridge-lesson-factory`): 좋은 교안의 구조·언어·품질 계약과 산출물 QA
- **Pipeline** (이 저장소): 사람 승인 순서, 다음 단계 실행 권한, Factory 검증 결과의 연결

## 핵심 원칙

1. 한 번에 하나의 활성 교안만 운영합니다(WIP=1).
2. 승인되지 않은 차시를 건너뛰지 않습니다.
3. 모든 차시 상세 설계가 승인되기 전에는 PPTX 제작을 허용하지 않습니다.
4. PPTX 제작 허용 전에는 실습도구 제작을 허용하지 않습니다.
5. `stage` 문자열을 사람이 직접 올리는 방식으로 승격하지 않습니다. `pipelinectl`이 승인 기록에서 현재 milestone을 계산합니다.
6. Factory의 content-design 검증은 **정확한 commit SHA에 고정**합니다. `main`, `latest` 같은 움직이는 ref를 production 승인 근거로 사용하지 않습니다.
7. Pipeline은 PPTX/HTML/학교자료/개인정보를 저장하지 않습니다. 승인 상태와 공개 가능한 포인터만 저장합니다.
8. 실제 ChatGPT `handoff.json`은 private/local에 두고, Pipeline에는 내용이 아니라 **SHA·designState·승인된 차시 번호만** 남깁니다.

## 설계 승인 흐름

```text
CLEAN_INTAKE
→ COURSE_MAP_APPROVED
→ SESSION_1_APPROVED
→ SESSION_2_APPROVED
→ ...
→ ALL_CONTENT_APPROVED
→ PPTX_BUILD_ALLOWED
→ PRACTICE_TOOL_BUILD_ALLOWED
```

차시 수는 교안마다 다를 수 있으므로 `SESSION_N_APPROVED`는 동적으로 계산합니다.

## ChatGPT handoff lineage

ChatGPT 교안 대화에서 나온 실제 `handoff.json`은 Factory가 먼저 검증합니다. Pipeline의 `handoff_lineage.py`는 정확한 Factory commit에서 그 검증기를 실행한 뒤 public-safe 요약만 만듭니다.

```bash
python3 tools/handoff_lineage.py \
  --handoff /private-work/course/handoff.json \
  --factory-root ../nextbridge-lesson-factory \
  --factory-commit <40-char-sha> \
  --captured-at 2026-08-16T22:00:00+09:00 \
  --out handoffs/course-id.json
```

생성되는 lineage에는 학생 화면 문장이나 교사 대본이 없습니다. `handoffSha256`, `designState`, `approvedSessions`, Factory commit만 기록합니다. 실제 상세 handoff는 public Git에 커밋하지 않습니다.

## 빠른 실행

```bash
python3 -m unittest discover -s tests -v
python3 tools/pipelinectl.py validate --state fixtures/pipeline/pass/state.json
python3 tools/pipelinectl.py status --state fixtures/pipeline/pass/state.json
python3 tools/pipelinectl.py check --state fixtures/pipeline/pass/state.json --to ALL_CONTENT_APPROVED
```

Factory checkout이 준비된 환경에서는 design bundle까지 검증합니다.

```bash
python3 tools/pipelinectl.py factory-check \
  --state fixtures/pipeline/pass/state.json \
  --factory-root ../nextbridge-lesson-factory
```

## 저장소 경계

이 저장소가 판단하는 것:

- 승인 순서가 맞는가
- 다음 작업을 시작해도 되는가
- Factory 검증 대상이 정확한 commit SHA에 고정되어 있는가
- 한 차시를 건너뛰거나 build gate를 우회하지 않았는가
- private ChatGPT handoff와 공개 lineage가 같은 SHA를 가리키는가

이 저장소가 판단하지 않는 것:

- 학생 화면 문장이 좋은가
- 개념이 교육적으로 정확한가
- PPTX가 예쁜가
- HTML이 기술적으로 정상인가

위 품질은 Factory가 담당합니다.
