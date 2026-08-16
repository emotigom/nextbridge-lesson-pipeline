# ChatGPT handoff lineage

실제 `handoff.json`은 상세 교안 문장과 교사 대본을 포함할 수 있으므로 이 디렉터리에 넣지 않습니다.

새 교안 제작 중 public Git에 남길 필요가 있을 때만 아래 형태의 **요약 lineage**를 저장합니다.

```text
handoffs/<courseId>.json
```

포함 가능:

- `courseId`
- handoff SHA-256
- 현재 `designState`
- 전체 차시 수
- 승인된 차시 번호
- handoff를 검증한 Factory commit SHA

포함 금지:

- 학생 화면 문장
- 교사 대본
- 대화 전문
- 학교 원본 자료
- 학생·교사 개인정보

lineage는 `tools/handoff_lineage.py`로 생성합니다. 사람이 handoff 내용을 요약해서 옮기지 않습니다.
