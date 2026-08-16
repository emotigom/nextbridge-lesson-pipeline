# Course pipeline states

실제 교안의 orchestration 상태는 아래 경로에 둡니다.

```text
courses/<courseId>/state.json
```

이 디렉터리에는 승인 상태, Factory의 정확한 commit SHA, 공개 가능한 candidate 해시만 둡니다.

넣지 않는 것:

- PPTX / PDF / HTML / ZIP
- 상세 storyboard 원문
- 학교 원본 자료
- 학생·교사 개인정보
- 비공개 수동 Gate 증거

현재 첫 실제 상태는 `courses/feed-why/state.json`입니다. 이 상태는 clean-room 설계와 PPTX/실습도구 제작 승인까지 완료된 사실을 기록하지만, Factory의 runtime release `FIELD_READY/CANONICAL` 승인을 대신하지 않습니다.
