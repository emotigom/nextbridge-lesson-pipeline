# CI execution boundary

Pipeline CI가 실행하는 외부 저장소 코드는 `emotigom/nextbridge-lesson-factory`로 고정합니다.

- `factory.repository`는 다른 값이면 hard fail합니다.
- `factory.commitSha`는 정확한 40자리 commit SHA여야 합니다.
- GitHub Actions의 `repository:` 값은 상태 파일에서 동적으로 받지 않습니다.
- 상태 파일에서는 신뢰 저장소 내부의 어떤 commit을 검증할지만 선택합니다.
- build gate에서는 해당 SHA를 checkout한 뒤 Factory의 content-design 검사를 다시 실행합니다.

이 경계는 pull request가 임의 외부 저장소를 지정하여 CI에서 코드를 실행하는 supply-chain 경로를 막기 위한 것입니다.
