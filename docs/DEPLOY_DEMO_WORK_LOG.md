# 배포 버전 확인 API

## 2026-11-18

- 기존 컨트롤러와 같은 `@Tag`, `@Api`, `ResponseEntity` 형식으로 `GET /common/deploy-demo`를 추가한다.
- 응답 DTO를 같은 Kotlin 파일에 선언해 한 파일만 추가하면 실행된다. `version`은 수업 실습 버전이고 `pod`는 실행 중인 컨테이너의 `HOSTNAME`이다.
- PR 검사 통과 후 main에 병합하고 기존 CI → ECR → Image Updater → Git 커밋 → Argo CD → EKS 연결로 새 Pod가 배포되는지 확인한다.
- 배포 전후 Pod 교체, Ready 전환, 기존 Pod 종료, 같은 Service 주소의 health 응답과 MySQL·PVC 유지를 비교한다. 실제 운영 검증 자료는 비공개로 보관한다.

업데이트 위치: `src/main/kotlin/com/ideasupport/main/common/health/DeployDemoController.kt`. 다음 실습에서는 이 파일의 `team-v1`을 `team-v2`로 바꾼다.

## 2026-11-18 team-v2 재배포

- 현재 main에서 새 PR을 만들어 배포 확인 버전을 `team-v1`에서 `team-v2`로 변경한다.
- PR 검사 후 병합하고 기존 CI·Image Updater·Argo CD를 통한 자동 배포를 확인한다.
- 같은 Service 주소에서 버전 변경과 새 Pod 교체, health 응답 및 MySQL·PVC 유지를 대조한다. 실제 운영 검증 자료는 비공개 기록으로 보관한다.

업데이트 위치: 위 `DeployDemoController.kt`의 `version` 값.
