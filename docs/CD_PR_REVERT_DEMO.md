# 2026-11-11 dev PR 배포와 웹 Revert 실습

## 변경과 확인 기준

- 사용자 요청으로 실제 dev 대상 PR을 만들고 merge·자동 배포한 다음, GitHub 웹 Revert로 복구 PR을 만들어 다시 dev에 merge한다.
- 화면 확인용 변경은 Swagger API 표시 버전 `v1.0` → `v1.1` 한 줄이다. Gradle 프로젝트 버전이나 업무 API·DB는 변경하지 않는다.
- 배포 대상은 예시 공간 `https://daelim.minq.live/example/`이다. team1~team8의 앱은 이 저장소의 dev 배포 대상이 아니다.
- 업데이트 후 `/example/v3/api-docs/common`의 `info.version`이 `v1.1`, 복구 배포 후 `v1.0`인지 확인한다. `/example/common/health`의 `status: ok`, `database: up`도 함께 확인한다.
- PR 검사 성공과 dev merge 후 배포 성공을 구분한다. 두 배포의 dev merge SHA, `dev-전체SHA` 이미지 태그, digest, Actions 링크를 최종 기록한다.

## 진행 상태

실습용 변경을 준비했다. PR 번호·실제 배포 결과·웹 Revert 결과는 각 단계를 완료한 뒤 갱신한다. 아직 두 배포가 끝났다는 뜻은 아니다.

업데이트 위치: 이 문서, 11주차 CD Notion 활동 STEP 2의 6번, `docs/DEV_ROLLBACK_WEB.md`의 실제 사례. 다음 주 예고를 추가하지 않는다.
