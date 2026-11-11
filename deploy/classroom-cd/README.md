# 11주차 공유 dev 배포 환경

2026-11-10 확정: **이번 주 dev는 Lightsail VM + Docker Compose로 완료하고 EKS는 다음 주에 진행한다.** EKS는 생성하지 않았다. main workflow는 기존 ECR 업로드까지만 수행한다.

## 실제 운영 주소

- 앱: `https://daelim.minq.live/example/`, `https://daelim.minq.live/team1/`~`https://daelim.minq.live/team8/`.
- 상태 확인: 위 주소 뒤 `common/health`. Swagger: 위 주소 뒤 `swagger-ui/index.html`.
- Registry: `https://docker.minq.live` (기존 EC2 유지).
- 예시 이미지: `docker.minq.live/team/idea-support-server:latest`. 학생은 `team1`~`team8`.
- VM: 계정 `950177940921`, 시드니 `ap-southeast-2`, `classroom-dev-compose`, Ubuntu 24.04, `large_3_2` 2 CPU·8GB·160GB, USD44/월(추가 사용량·세금 별도).
- 고정 IP `13.55.177.148`, 사설 IP `172.26.7.237`. GoDaddy의 `daelim.minq.live` A 레코드와 Caddy HTTPS를 사용한다.

Lightsail **VM은 서버리스가 아니다**. 묶음 요금의 가상 서버이며 OS·Docker·MySQL·백업을 직접 관리한다. Lightsail Container Service는 다른 상품이다. 한 대를 공유하므로 서버 장애는 모든 팀에 영향을 준다. 부하 시험이나 고가용성 검증을 완료한 환경은 아니다.

## 8팀 사용 방법

학생은 AWS 로그인이나 SSH 없이 자기 팀 GitHub 저장소의 `dev` Environment를 설정한다. 현재 자동 배포는 예시 저장소 `MinQDU014/idea-support-server`에 연결돼 있다. 강사는 각 팀에 **그 팀의 항목만** 전달한다. 전체 파일을 학생에게 공유하지 않는다.

| 종류 | GitHub 이름 | 예시 / 팀1 |
| --- | --- | --- |
| Variables | `DEV_REGISTRY_HOST` | `docker.minq.live` |
| Variables | `DEV_REGISTRY_NAMESPACE` | `team` / `team1` |
| Variables | `DEV_DEPLOY_URL` | `https://daelim.minq.live/_cd/team` / `.../_cd/team1` |
| Secrets | `DEV_REGISTRY_USER`, `DEV_REGISTRY_PASSWORD` | 로컬 `team-access.json`의 자기 팀 값 |
| Secrets | `DEV_DEPLOY_TOKEN` | 로컬 `cd-access.json`의 자기 팀 값 |

`dev` push → 검사·테스트 → Jib 이미지 업로드(`latest`와 `dev-전체커밋`) → HTTPS 배포 요청 → 해당 팀 앱만 교체 → DB 포함 상태 확인 순서다. PR은 검사·테스트만 한다. `latest`는 최신 별칭으로 유지하며 실제 실행 이미지는 **digest로 고정**한다. Registry는 최초 push 시 팀 이미지 경로가 생긴다.

최초 9개 앱(8팀+예시)은 검증된 같은 예시 이미지로 시작한다. 자기 팀 첫 CI 성공 후 해당 팀 이미지로 바뀐다. Registry Basic Auth는 namespace별 쓰기 ACL이 아니므로 교육용 신뢰 관계에서만 공유한다. Compose 역시 강한 다중 사용자 격리 환경은 아니다. 팀 배포 토큰은 자기 팀의 고정 이미지 경로와 고정 Compose 프로젝트만 제어한다.

실제 `team-access.json`·`cd-access.json`은 백엔드 루트와 로컬 `.local/`에 보관하며 Git에서 제외한다. 공개 예제에는 가짜 값만 넣는다. DB 비밀값과 앱 키는 서버 `/opt/classroom-cd/credentials.json` 및 팀별 `.env.dev`에만 두고 학생·Git·Notion에 공개하지 않는다.

## 서버 구성과 관리

- `/opt/classroom-cd/infra.json`: MySQL 8.4·Caddy, 이미지 digest 고정. MySQL 데이터는 `mysql-data`, 인증서는 `caddy-data`에 영속 저장한다.
- `/opt/classroom-cd/teamN/compose.json`: 팀별 프로젝트. 메모리 제한 768MiB, JVM heap 256MiB, DB pool 3. 앱 포트는 loopback `18080`~`18088`에만 매핑한다.
- Caddy는 host network에서 HTTPS 경로를 해당 loopback 포트로 전달하고 `X-Forwarded-Prefix`를 설정한다. Swagger의 서버 URL도 팀 경로를 유지한다.
- 예시 DB `idea_team_dev`·`idea_team_main`, 팀1 `idea_team1_dev`·`idea_team1_main`처럼 dev/main을 별도 DB·사용자로 분리했다. 총 18개이며 main DB는 다음 주용으로 예약했다. 현재 EKS 앱은 없다.
- MySQL은 사설 IP에만 bind한다. 공인 3306은 열지 않았다. Docker 방화벽은 사설 3306의 외부 인터페이스 유입을 default VPC CIDR로 제한한다. **VPC peering은 생성하지 않았다.**
- SSH는 관리자 단일 IP만 허용한다. 승인받아 임시 사용한 Lightsail 브라우저 SSH 경로는 다시 닫았다. 학생 키·관리 계정·Bastion은 만들지 않는다.
- 강사 접속은 [브라우저 SSH·PowerShell 외부 SSH 안내](../../docs/LIGHTSAIL_SSH_ACCESS.md)를 따른다. 2026-11-11 사용자는 계정의 지역 제한을 확인한 뒤 서울 이전을 취소하고 현재 시드니 서버·IP를 유지하기로 했다.
- `classroom-deploy.service`: loopback 전용 수신기. TLS·팀별 인증, 이미지 경로 검증, 고정 명령 인자, 요청 크기 제한, 전역 배포 직렬화, 상태 확인·이전 이미지 복구를 수행한다. 결과는 팀별 `deployment-result.json`에 남긴다.
- `classroom-db-firewall.service`: Docker 재기동 후 DB 방화벽 적용. `classroom-db-backup.timer`: 매일 18:00 UTC(한국 03:00), 서버 내 압축 SQL 백업 7일 보관. **같은 VM의 백업이므로 서버 유실 대비 외부 백업·복구 검증은 별도 과제다.**

## GitHub 웹에서 PR을 되돌려 자동 재배포하기

학생은 [실제 SHA 예시·화면별 웹 실습 안내](../../docs/DEV_ROLLBACK_WEB.md)를 따른다. BAD_COMMIT_SHA는 되돌릴 변경의 커밋 번호를 넣는 자리표시자다. 실제 설명용 SHA `fd0e2b707be3c7d768b4ca04dbf7e0129b575f80`와 GitHub 원문 링크·복사 아이콘 화면을 안내에 넣었다. 이 문서 커밋 자체를 실습 복구 대상으로 사용하지 않는다.

이번 주 주 경로는 **Pull requests → Closed → dev에 합쳐진 실습 PR → Revert → 복구 PR의 base: dev·Files changed 확인 → Create pull request → Checks 통과 → Merge pull request → Confirm merge → Actions → 자기 팀 health**다. 터미널·Python·SSH가 필요하지 않다.

예시 저장소에는 2026-11-11 조회 기준 merged PR이 없다. 학생 저장소에서 dev 기준 실습 브랜치를 만들고 README 문장 한 줄을 추가한 PR을 dev에 합치는 준비부터 진행한다. 실습 커밋에는 skip ci 지시를 넣지 않는다. 웹 Revert는 합쳐진 PR을 대상으로 하며 일반 커밋 화면에 버튼이 있다고 안내하지 않는다.

Revert 버튼만으로는 dev가 바뀌지 않는다. 복구 PR이 dev에 merge돼야 현재 workflow의 검사·새 이미지 업로드·팀 앱 교체·health가 실행된다. 새 Revert 커밋 번호의 태그와 latest가 갱신되고 실제 배포 digest를 Actions 요약에서 확인한다. 코드 복구가 DB 스키마·데이터 복원을 뜻하지는 않는다.

안내의 SHA 화면은 실제 예시 저장소를 캡처했다. Revert·Merge 버튼 그림은 출처를 표시한 GitHub 공식 문서 예시이며 우리 저장소에서 실제 복구 PR을 실행한 화면으로 제시하지 않는다. 운영용 API·보조 도구와 GitHub Environment의 배포 토큰은 유지한다.

## 설치 도구와 검증

최초 생성: `provision-lightsail.py --region 대상리전` → 관리자 SSH에서 `bootstrap-ubuntu.sh` → `install-compose.py` → `install-controller.py` → `install-maintenance.py`. 리전은 반드시 명시하며 `--plan-only`로 생성 전 점검할 수 있다. 비밀 파일을 인자로 전달하고 HTTPS 도메인으로 설치한다. 전체 재설정은 강사만 수행하며 팀별 배포에는 설치 도구를 재실행하지 않는다.

2026-11-11 [서울 이전 검토 이력](../../docs/LIGHTSAIL_SEOUL_MIGRATION.md): 앱·18개 DB·8팀 설정의 비공개 예비 백업을 확보했으나, 계정의 시드니 고정 프로젝트 제한을 확인한 뒤 사용자가 이전을 취소했다. Paid plan 전환·고급 기능 활성화·서울 생성·시드니 삭제·DNS 변경은 하지 않는다. 현재 시드니 구성과 도메인을 유지한다.

최초 launch script는 Lightsail의 `/bin/sh` 래퍼에서 bash 전용 `pipefail`로 중단됐다. 생성 도구는 POSIX 구문으로 수정했고 실제 VM은 관리 SSH bootstrap으로 설치했다. 이전 cloud-init 오류 이력과 현재 정상 상태는 구분한다.

`verify-server.py`: 9개 HTTPS health·Swagger와 18개 DB의 자기 DB 허용/다른 팀·다른 환경 DB 거절을 검증한다. `test-deploy-server.py`: 다른 팀 이미지·임의 명령 문자열 거절과 실패 시 선택한 팀만 복구하는 동작을 검증한다. `verify-maintenance.py`: 백업 gzip 무결성·18개 DB 포함과 유지관리 서비스 상태를 확인한다. DB 복원·부하·실기기 설치 시험은 수행하지 않았다.

검증 결과: `docs/evidence/classroom-cd/`. [실제 Actions 42836332717](https://github.com/MinQDU014/idea-support-server/actions/runs/42836332717)의 검사·테스트·이미지 업로드·앱 교체·외부 health가 성공했다. 최신 태그와 실행 digest가 일치함을 별도로 확인했다. 다음 주 초안 `EKS_REVIEW.md`·생성 템플릿은 적용·검증 완료 자료가 아니다.

## 업데이트 위치

학생: `.github/workflows/dev-registry.yaml`과 GitHub `dev` Environment. 강사: 이 디렉터리·서버 `/opt/classroom-cd/`·로컬 비밀 파일. 강의: [11주차 CD Notion](https://app.notion.com/p/project-2026-01/11-CD-40d9fa2a819d801ebbbbf605cc00843f). main/EKS는 다음 주 별도 진행한다.
