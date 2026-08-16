# ADR-0001 — Factory와 Pipeline의 책임을 분리한다

- 상태: Accepted
- 결정일: 2026-08-16

## 맥락

교안 제작에는 서로 다른 두 문제가 있다.

1. 좋은 교안인가: clean-room 입력, 차시 구조, 학생 화면 언어, 경험 뒤 개념, 시간 구조, 품질 점수
2. 지금 다음 작업을 시작해도 되는가: 차시별 승인 순서, 전체 콘텐츠 승인, PPTX/실습도구 제작 허용

두 문제를 같은 저장소와 같은 상태 문자열로 처리하면 기술 QA와 교육 승인 의미가 섞이고, 사람이 stage 문자열을 바꾸는 것만으로 다음 제작 단계가 열릴 위험이 있다.

## 결정

1. `nextbridge-lesson-factory`는 **품질 계약과 검증 엔진**이다.
2. `nextbridge-lesson-pipeline`은 **승인 순서와 실행 권한 관리자**다.
3. Pipeline의 Factory 참조는 반드시 40자리 commit SHA에 고정한다.
4. Pipeline은 승인 기록에서 milestone을 계산한다. 사람이 별도 `stage` 문자열을 편집하지 않는다.
5. 차시 승인은 1번부터 연속되어야 한다. 중간 차시를 건너뛴 승인은 hard fail이다.
6. `ALL_CONTENT_APPROVED` 전에는 `PPTX_BUILD_ALLOWED`가 될 수 없다.
7. `PPTX_BUILD_ALLOWED` 전에는 `PRACTICE_TOOL_BUILD_ALLOWED`가 될 수 없다.
8. 전체 콘텐츠 승인 이후의 build gate에서는 고정된 Factory commit의 content-design 검증을 다시 실행한다.
9. Pipeline public Git에는 실제 PPTX/HTML/학교자료/개인정보를 저장하지 않는다.

## 상태 해석

`SESSION_N_APPROVED`는 고정 enum이 아니라 `sessionCount`와 연속 승인 수에서 계산한다. 따라서 3차시·4차시·8차시 교안에 같은 도구를 사용할 수 있다.

```text
CLEAN_INTAKE
→ COURSE_MAP_APPROVED
→ SESSION_1_APPROVED
→ ...
→ SESSION_N_APPROVED
→ ALL_CONTENT_APPROVED
→ PPTX_BUILD_ALLOWED
→ PRACTICE_TOOL_BUILD_ALLOWED
```

## 사람 승인

승인 레코드가 `APPROVED`이면 `reviewer`와 `approvedAt`이 반드시 존재해야 한다. 자동 QA는 사람 승인을 만들어내지 않는다.

## 후속 작업

실제 `feed-why` 상태 파일과 이번 clean-room 교안의 Factory design bundle 연결은 별도 migration PR에서 수행한다.
