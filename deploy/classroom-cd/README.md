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
- `classroom-deploy.service`: loopback 전용 수신기. TLS·팀별 인증, 이미지 경로 검증, 고정 명령 인자, 요청 크기 제한, 전역 배포 직렬화, 상태 확인·이전 이미지 복구를 수행한다. 결과는 팀별 `deployment-result.json`에 남긴다.
- `classroom-db-firewall.service`: Docker 재기동 후 DB 방화벽 적용. `classroom-db-backup.timer`: 매일 18:00 UTC(한국 03:00), 서버 내 압축 SQL 백업 7일 보관. **같은 VM의 백업이므로 서버 유실 대비 외부 백업·복구 검증은 별도 과제다.**

강사 수동 교체·복구는 해당 팀 compose.json의 image만 지정 버전으로 바꾼 후 다음 명령을 실행한다. 공유 MySQL이나 데이터 볼륨을 삭제하지 않는다.

```sh
sudo docker compose -p team1 -f /opt/classroom-cd/team1/compose.json pull app
sudo docker compose -p team1 -f /opt/classroom-cd/team1/compose.json up -d --no-deps app
curl --fail https://daelim.minq.live/team1/common/health
```

학생은 강사에게 자기 팀 항목만 담긴 `cd-access.json`을 받아 Git에서 제외한 백엔드 루트에 둔다. Python 3에서 다음과 같이 기존 커밋 태그 또는 digest를 요청하면 SSH 없이 복구할 수 있다. `FULL_COMMIT_SHA`는 실제 기존 태그의 전체 커밋 번호로 바꾼다.

```sh
python deploy/classroom-cd/request-deploy.py --team team1 --image docker.minq.live/team1/idea-support-server:dev-FULL_COMMIT_SHA
```

앱 이미지 복구는 DB 스키마나 데이터를 되돌리지 않는다. 학생 실습에 `docker compose down -v`를 넣지 않는다.

## 설치 도구와 검증

최초 생성: `provision-lightsail.py` → 관리자 SSH에서 `bootstrap-ubuntu.sh` → `install-compose.py` → `install-controller.py` → `install-maintenance.py`. 비밀 파일을 인자로 전달하고 HTTPS 도메인으로 설치한다. 전체 재설정은 강사만 수행하며 팀별 배포에는 설치 도구를 재실행하지 않는다.

최초 launch script는 Lightsail의 `/bin/sh` 래퍼에서 bash 전용 `pipefail`로 중단됐다. 생성 도구는 POSIX 구문으로 수정했고 실제 VM은 관리 SSH bootstrap으로 설치했다. 이전 cloud-init 오류 이력과 현재 정상 상태는 구분한다.

`verify-server.py`: 9개 HTTPS health·Swagger와 18개 DB의 자기 DB 허용/다른 팀·다른 환경 DB 거절을 검증한다. `test-deploy-server.py`: 다른 팀 이미지·임의 명령 문자열 거절과 실패 시 선택한 팀만 복구하는 동작을 검증한다. `verify-maintenance.py`: 백업 gzip 무결성·18개 DB 포함과 유지관리 서비스 상태를 확인한다. DB 복원·부하·실기기 설치 시험은 수행하지 않았다.

검증 결과: `docs/evidence/classroom-cd/`. [실제 Actions 42836332717](https://github.com/MinQDU014/idea-support-server/actions/runs/42836332717)의 검사·테스트·이미지 업로드·앱 교체·외부 health가 성공했다. 최신 태그와 실행 digest가 일치함을 별도로 확인했다. 다음 주 초안 `EKS_REVIEW.md`·생성 템플릿은 적용·검증 완료 자료가 아니다.

## 업데이트 위치

학생: `.github/workflows/dev-registry.yaml`과 GitHub `dev` Environment. 강사: 이 디렉터리·서버 `/opt/classroom-cd/`·로컬 비밀 파일. 강의: [11주차 CD Notion](https://app.notion.com/p/project-2026-01/11-CD-40d9fa2a819d801ebbbbf605cc00843f). main/EKS는 다음 주 별도 진행한다.
