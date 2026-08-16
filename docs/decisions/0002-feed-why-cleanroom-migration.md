# ADR-0002 — feed-why를 clean-room proof 기반 실제 Pipeline 상태로 등록한다

- 상태: Accepted
- 결정일: 2026-08-16

## 결정

1. `courses/feed-why/state.json`을 첫 실제 course orchestration 상태로 등록한다.
2. Factory는 `79fa84068011035f7546a0f46090715eb278a6d4`에 고정하고 `PRIVATE_PROOF` 모드로 `courses/feed-why/design/cleanroom-v1/design-proof.json`을 검증한다.
3. 상태 파일에는 최종 package/PPTX/practice-tool/activity-pack SHA-256을 기록하고 Factory proof의 artifact SHA와 일치해야 한다.
4. 기존 채팅에서 완료된 clean intake, course map, 1~4차시 승인, 전체 콘텐츠 승인, PPTX 제작, 실습도구 제작을 migration 시점에 `emotigom`의 공식 승인 기록으로 옮긴다.
5. 현재 milestone은 `PRACTICE_TOOL_BUILD_ALLOWED`다.
6. 이 milestone은 제작 순서 승인이다. Factory의 runtime `FIELD_READY`, 권리 검증, Windows/브라우저 수동 Gate, 공개 배포 승인을 대신하지 않는다.

## 공개/private 경계

Pipeline에는 상태와 SHA만 둔다. 상세 storyboard, PPTX, HTML, PDF, 미디어 및 private evidence는 저장하지 않는다.
