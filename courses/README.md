# Course pipeline states

실제 교안의 orchestration 상태는 아래 경로에 둡니다.

```text
courses/<courseId>/state.json
```

이 디렉터리에는 승인 상태와 Factory 포인터만 둡니다.

넣지 않는 것:

- PPTX / PDF / HTML / ZIP
- 학교 원본 자료
- 학생·교사 개인정보
- 비공개 수동 Gate 증거

현재 PR은 Pipeline 엔진 bootstrap만 수행하므로 실제 `feed-why/state.json`은 아직 만들지 않습니다. 해당 migration은 다음 통합 PR에서 수행합니다.
