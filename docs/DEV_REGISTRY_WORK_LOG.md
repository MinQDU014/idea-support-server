# dev Registry 적용 기록

## 2026-11-10

- 작업 전 최신 커밋 `232ec5e`의 변경 문서 `docs/TESTING_AND_DEMO.md`, 현재 README, Jib 설정과 main ECR workflow를 읽었다.
- 사용자가 지정한 `dev` 브랜치에 개발 이미지 업로드를 추가한다. 기존 main ECR workflow는 수정하지 않는다.
- 최종 구성: 강의용 AWS 계정의 시드니 EC2 t3.micro 한 대, Registry 한 개, HTTPS·조회 화면용 Caddy 한 개, 암호화한 gp3 40GiB.
- 팀은 `team1/idea-support-server`~`team8/idea-support-server` 이름으로 구분한다. 기본 로그인 인증은 공유 접근이며 팀별 경로 권한 분리는 하지 않는다.
- 고정 IP `52.65.110.152`, 도메인 `docker.minq.live`. HTTPS 443과 관리자 IP의 SSH만 허용한다. Registry 5000과 평문 HTTP는 외부에 공개하지 않는다.
- Caddy의 TLS-ALPN-01 인증서 자동 발급·갱신을 사용한다. 공식 컨테이너 이미지는 실제 digest로 고정했다.
- GitHub `dev` Environment를 dev 브랜치로 제한했다. 예제 저장소는 team1 경로를 사용한다. 계정과 비밀번호는 Secrets에 저장하고 문서에는 기록하지 않았다.
- workflow는 PR에서 스타일·테스트만 실행하고 검사를 통과한 dev push에서만 Jib으로 업로드한다. 수동 실행과 앱 프로필도 dev로 한정한다.
- 태그는 `dev-커밋전체번호`와 이동 가능한 `dev`다. CD는 이후 같은 이미지 주소나 digest를 지정해 실행한다. 이번 변경 자체는 앱을 실행하지 않는다.

## 검증

- CloudFormation 정적 검사, Python 문법 검사, 실제 서버의 실행 설정 검사 통과.
- 서버 내부에서 인증 요구·잘못된 비밀번호 거절·조회 화면·8팀 동시 약 2MiB 레이어 push 및 manifest 읽기 통과.
- 실제 외부 HTTPS에서 같은 8팀 동시 검사 통과: 8.93초. [검증 결과](evidence/dev-registry/registry-verification.json).
- team1 계정으로 team2 이미지도 읽을 수 있는 공유 접근 특성을 확인했다. 검증 이미지는 `teamN/registry-smoke:verify-*`이며 앱 이미지가 아니다.
- 작은 OCI 이미지의 기본 동작·동시성 확인이며, 실제 앱 8개 전체 빌드 부하나 장시간 성능을 보장하는 시험은 아니다.
- 설치 도구를 기존 서버에 다시 실행해도 계정·이미지·인증서와 pinned digest를 유지했다. 재실행 후 실제 HTTPS에서 기존 앱 이미지 digest가 그대로인지 확인했다.
- [실제 GitHub Actions](https://github.com/MinQDU014/idea-support-server/actions/runs/42754201601) 성공: 스타일 검사와 테스트 189개 통과, 실패·건너뜀 0. 테스트 작업의 Gradle 실행 1분 56초, Jib 작업 2분 3초.
- 앱 이미지 `docker.minq.live/team1/idea-support-server:dev-5138d05492002dd81773e3cc61e6a2893d132479`와 `dev`의 digest가 일치했다. amd64·arm64 두 플랫폼의 이미지 설정에서 dev 프로필을 확인했다. [앱 이미지 검증](evidence/dev-registry/app-image-verification.json).
- 이미지 digest: `sha256:d41f6c043d736c8b5b1b836b8a3b2e74627d06a24f7ec0fd240203bfaace040f`. 앱 컨테이너 실행은 이번 범위에 포함하지 않았다.
- 10주차 CI Notion 페이지에 브랜치 기준 수정, 공유 Registry 설명, 실제 주소, 팀별 이미지 표, Mermaid 구성도와 CD 연결 방법을 반영했다.
- 연결 기기 설치·확인은 사용자 지시에 따라 생략했다. 이후 문서·증거만 기록하는 커밋에는 `[skip ci]`를 사용해 같은 앱 테스트와 이미지 생성을 반복하지 않는다.

## 업데이트 위치

- CI: `.github/workflows/dev-registry.yaml`, GitHub `dev` Environment.
- 서버·화면: `deploy/dev-registry/`, EC2 `/opt/classroom-registry/compose.json`·`Caddyfile`.
- 이미지: EC2 `/data/registry`, 인증서: `/data/caddy`.
- 강의: `docs/DEV_REGISTRY.md`와 10주차 CI Notion 페이지.
- 월 비용 추정: USD 17.126 + 전송량·세금 등, 크레딧 적용 전. 정지 후에도 디스크·고정 IP 비용은 남으며 종료 시 보존한 디스크도 따로 정리한다.

서버 인스턴스: `i-03e17334bb0666018`. CloudFormation 스택 `classroom-dev-registry`는 CREATE_COMPLETE다.

## 2026-11-10 이미지 초기화와 학생 접속 검토

- 사용자 요청으로 Registry에 업로드된 모든 이미지를 삭제했다. 삭제 전 앱 이미지 저장소 1개와 검증용 저장소 8개, 총 9개였다.
- 실행 중인 Registry의 bind mount가 `/data/registry` → `/var/lib/registry`임을 확인했다. 쓰기를 막기 위해 서비스 두 개를 잠시 정지하고 해당 이미지 데이터만 비운 뒤 재시작했다.
- 외부 HTTPS에서 catalog가 빈 배열이며 이전 9개 저장소의 태그 조회가 모두 404임을 확인했다. 인증 후 사이트 응답은 200이다. 이미지 데이터 공간은 약 632MiB에서 4KiB로 줄었다.
- Registry·Caddy 운영 컨테이너, HTTPS 인증서, 로그인 계정은 유지했다. 기존 앱 업로드 검증 결과는 당시의 이력이며 현재 Registry에는 그 이미지가 없다. 다음 dev CI 업로드 시 새 이미지가 다시 생긴다.
- [삭제 후 검증](evidence/dev-registry/registry-clear-verification.json).
- 사용자는 학생별 직접 접속과 서로 다른 네트워크 사용을 확인했다. 권장안은 SSM 터널을 통한 SSH와 학생별 Linux 계정·키다. Bastion과 개인 키는 각각 접속 경로와 인증 수단으로 구분한다.
- [학생 EC2 접속 안내](EC2_STUDENT_ACCESS.md)에 관리자 접속, 학생 키 생성, SSM을 통한 SSH의 사전 조건과 예시를 정리했다. 학생용 SSM 역할·IAM 권한·Linux 계정은 아직 생성·적용하지 않았다.
- 현재 서버에서 공개 키 인증 활성화와 비밀번호 인증 비활성화, SSM Agent 서비스가 enabled임을 확인했다. Agent 존재만으로 학생용 SSM 접근이 준비된 것은 아니다.
- 기존 화면 파일의 별도 미커밋 변경은 수정하지 않았다. 이번 정리 후 업로드 검사를 다시 실행해 이미지를 재생성하지 않는다.

업데이트 위치: 이미지 초기화 결과는 이 문서와 검증 JSON, 접속 안내는 `EC2_STUDENT_ACCESS.md`. 실제 학생 접속 적용에는 학생별 AWS 로그인·공개 키와 허용 작업 범위가 필요하다.

## 2026-11-10 최종 단순화 — GitHub에서 Registry로 업로드

- 사용자가 학생용 SSH·SSM 구성을 취소하고 기존 Registry 업로드 실습으로 단순화했다. 학생용 AWS 로그인·Linux 계정·Bastion은 생성하지 않는다.
- 번호 없는 `team/idea-support-server`를 강의 예시로 정했다. 학생은 같은 workflow에서 `DEV_REGISTRY_NAMESPACE=team1`~`team8` 중 자기 팀을 설정한다. main → ECR 구성은 변경하지 않았다.
- dev workflow의 namespace 검증에 예시 `team`을 추가했다. Registry 호스트 기본값은 `docker.minq.live`, namespace 기본값은 `team`이다. 실제 GitHub dev Environment도 `team`으로 바꿨다.
- 예시 경로와 학생 경로는 이미지 이름이며 로그인 계정과 별개다. 기존 발급 계정으로 예시 이미지를 올리며, 추가 계정이나 서버는 만들지 않는다.
- 제공된 실제 `team-access.json`을 백엔드 루트에 복사하고 원본과 일치함을 확인했다. 모든 경로의 해당 파일명을 `.gitignore`로 제외했다. 실제 비밀번호는 공개 문서·소스에 기록하지 않으며 공개 템플릿에는 가짜 값만 넣었다. CI는 팀별 GitHub Secrets를 사용한다.
- 조회 화면에 강의 예시와 1팀~8팀 선택을 추가하고 기본 선택을 예시로 변경했다. 기존 로컬 HTML 포맷 변경은 보존하고 이번 기능 변경만 Git에 반영한다.
- `actionlint`와 변경 공백 검사를 통과했다. 로컬 자격 증명이 Git에서 제외되는 것을 확인했다. 실제 CI 실행·Registry 확인 결과는 아래에 이어 기록한다.

업데이트 위치: `.github/workflows/dev-registry.yaml`, GitHub dev Environment, `deploy/dev-registry/index.html`, `docs/DEV_REGISTRY.md`, 로컬 전용 루트 `team-access.json`. 학생 접속 방식 문서는 최종 결정에 맞춰 정리했다.

### 최종 적용·검증

- 기능 커밋 `ff4a3808955f1ab9a35e5880580a2ce52054bb24`를 원격 dev에 반영했다. [실제 Actions](https://github.com/MinQDU014/idea-support-server/actions/runs/42821885235)는 검사·테스트 작업 2분 58초, 이미지 업로드 작업 1분 53초로 모두 성공했다.
- 실제 예시 이미지 `docker.minq.live/team/idea-support-server:dev`와 `dev-ff4a3808955f1ab9a35e5880580a2ce52054bb24`를 확인했다. 두 태그의 digest는 `sha256:a56a12ab1f4af0035f3bbe8646a2b9d6f5e0284a4526068a49199e8974bb0562`로 같다. amd64·arm64 두 플랫폼 모두 dev 프로필이다.
- 현재 catalog에는 예시 저장소 1개가 있다. 학생 저장소는 첫 이미지 업로드 시 생긴다. 검증용 registry-smoke 이미지를 다시 만들지 않았다.
- 학생 8개 계정 모두 외부 HTTPS에서 예시 태그를 정상 조회했다. 새 조회 화면은 HTTP 200이며 기본 선택은 강의 예시다. [비밀값 없는 검증 결과](evidence/dev-registry/classroom-upload-verification.json).
- 실제 계정 파일은 Git에 추적되지 않고 `.gitignore`로 제외된다. 공개 파일의 가짜 비밀번호 템플릿과 구분했다. 백엔드 앱 실행·학생 PC 설치 검사는 이 작업에서 수행하지 않았다.
- 마지막 결과 문서·검증 JSON만 `[skip ci]` 커밋으로 기록해 같은 앱 빌드와 이미지 업로드를 반복하지 않는다. 기존 로컬 HTML 포맷 변경은 미커밋 상태로 보존했다.

## 2026-11-10 최신 이미지 태그를 latest로 정정

- 사용자가 dev 브랜치에서도 가장 최근 이미지는 `latest`여야 한다고 정정했다. dev는 브랜치·앱 프로필로 유지하고, 최신 이미지 별칭은 `latest`로 변경했다. 버전 확인용 `dev-커밋전체번호` 태그는 함께 유지한다.
- 최신 커밋 `9c9a1b9`에서 변경된 강의 문서·작업 기록·검증 JSON을 읽고 수정했다.
- dev workflow의 Jib 추가 태그를 `dev`에서 `latest`로 바꾸고 Actions 요약에 최신 주소와 커밋별 주소를 모두 표시하도록 수정했다. README와 현재 강의 안내의 팀 1~8·예시 태그와 pull 명령도 갱신했다.
- 기존에 검사·업로드를 통과한 멀티 플랫폼 manifest를 Registry API로 `latest`에 등록했다. 외부 HTTPS에서 기존 이미지와 같은 digest인 `sha256:a56a12ab1f4af0035f3bbe8646a2b9d6f5e0284a4526068a49199e8974bb0562`를 반환함을 확인했다. [latest 검증 결과](evidence/dev-registry/latest-tag-verification.json).
- 기존 `dev` 태그는 이전 이력으로 남고 앞으로 workflow는 `latest`와 커밋별 태그를 갱신한다. amd64·arm64 이미지와 dev 프로필은 기존 검증 이미지와 동일하다.
- actionlint·Git 공백 검사를 통과했고 실제 비밀번호 파일의 Git 제외를 다시 확인했다. 앱 코드는 바뀌지 않아 기존에 통과한 전체 테스트·빌드는 반복하지 않고 태그 게시와 조회만 검증했다. 변경은 `[skip ci]`로 기록한다. 사용자 HTML 포맷 변경은 계속 보존한다.

업데이트 위치: `.github/workflows/dev-registry.yaml`, `README.md`, `docs/DEV_REGISTRY.md`, `docs/evidence/dev-registry/latest-tag-verification.json`. 학생도 자기 namespace에서 `:latest`를 사용한다.

## 2026-11-10 11주차 CD 구성 비교 검토

- 사용자 요청으로 dev의 자체 서버 배포와 main의 EKS 배포를 연결하는 학습 구성을 검토했다. 최신 커밋 ecb68f4에서 변경된 문서를 읽고 기존 main workflow가 ECR 업로드까지임을 확인했다.
- Notion connector는 404였으나 로그인된 브라우저에서 11주차의 6장·7장 배포·되돌리기 내용을 확인했다. 페이지는 수정하지 않았다.
- 공식 Docker·AWS·Kubernetes 자료로 EC2/Lightsail과 Compose/Swarm의 구분, 단일 서버 운영, EKS 팀별 공유 방식과 현재 가격을 확인했다.
- [CD 학습 구성 검토](CD_LEARNING_PLAN.md)에 제안·근거·8팀 구분·수업 순서·Notion 갱신 대상을 기록했다. 권장안은 dev 공유 실행 서버 + Compose, main 공유 EKS, Swarm 선택 비교다. 사용자 확정 전 제안이다.
- 인프라·권한·CI·배포 코드는 변경하지 않았다. 서버 생성·설치·EKS 배포·실기기 검증은 수행하지 않았다. 기존 HTML 미커밋 변경과 실제 계정 파일의 Git 제외를 유지했다.

## 2026-11-10 이번 주 CD — Lightsail VM + Compose 구축

- 사용자 확정: 이번 주 dev만 마무리하고 EKS 생성은 다음 주로 미룬다. EKS 클러스터·OIDC 배포 역할·VPC peering은 생성하지 않았다. main workflow는 기존 ECR 업로드 구성 그대로다.
- 강의 계정 950177940921의 Lightsail classroom-dev-compose(2 CPU·8GB·160GB, USD44/월)를 만들고 고정 IP 13.55.177.148을 연결했다. 사용자가 GoDaddy A 레코드를 등록한 daelim.minq.live에서 Caddy HTTPS가 정상이다.
- 관리자 키 등록 시 사용자 승인을 받아 Lightsail browser SSH를 잠시 허용했고, 로컬 SSH를 확인한 뒤 browser SSH 경로를 다시 닫았다. 현재 22번은 관리자 IP 59.14.52.80/32만 허용한다. 학생 SSH는 생성하지 않았다.
- 초기 launch script의 /bin/sh·pipefail 오류는 생성 도구에서 수정했다. 실제 VM은 관리 SSH bootstrap으로 Docker를 설치했고 기존 cloud-init 오류 이력은 보존한다.
- 공유 MySQL 한 개, 예시+8팀 Compose 앱 9개, HTTPS 팀별 경로를 실제 설치했다. 각 팀 dev/main DB·사용자를 분리해 총 18개를 만들었다. main DB는 다음 주용이며 EKS 앱은 없다.
- 모든 팀의 HTTPS health·Swagger가 200이고 DB 연결 및 mock 초기 데이터 준비가 정상이다. 18개 DB 사용자 모두 자기 DB에 접근 가능하고 다른 팀 및 반대 환경 DB는 Access denied임을 검증했다. 증거는 docs/evidence/classroom-cd/lightsail-verification.json.
- 팀별 CD 토큰과 고정 Compose 프로젝트·이미지 경로를 사용하는 HTTPS 배포 수신기를 설치했다. 잘못된 인증과 다른 팀 토큰은 401, 다른 팀 이미지는 400으로 거절하고 자기 예시 이미지의 요청은 200임을 실제 확인했다. 단위 검증 2개는 임의 이미지/명령 문자열 거절과 실패 시 해당 팀만 복구하는 동작을 통과했다. 실제 실패 이미지의 운영 복구/부하 시험을 했다고 표현하지 않는다.
- dev Actions에 이미지 업로드 다음 앱 교체·상태 확인을 연결했다. GitHub dev Environment에 예시 URL·배포 토큰을 설정했다. 학생은 자기 팀 Registry 비밀값과 CD 토큰만 설정하며 서버 키나 DB 비밀값을 받지 않는다. 실제 CI 결과는 후속 기록에 남긴다.
- 앱 JVM heap 256MiB, 컨테이너 제한 768MiB, DB pool 3으로 설정했다. 직렬 배포로 동시 JVM 기동을 제한한다. 유휴 9개 앱 메모리 측정 약 0.6GiB/앱은 부하 성능 보장이 아니다.
- MySQL은 사설 IP에만 노출하며 공인 3306은 닫았다. Docker DB 방화벽 서비스와 일일 서버 내부 압축 백업(7일 보관)을 설치하고 첫 백업을 만들었다. 외부 백업·재해 복구 검증은 별도다.
- 실제 cd-access.json도 백엔드와 로컬 .local에 저장하고 Git에서 제외했다. 공개 예제에는 가짜 토큰만 있다. 기존 HTML 포맷 미커밋 변경을 보존했다.

업데이트 위치: .github/workflows/dev-registry.yaml, GitHub dev Environment, deploy/classroom-cd/, 서버 /opt/classroom-cd/, 11주차 Notion. EKS 초안은 다음 주 참고용이고 적용·검증 완료 자료가 아니다.

### 이번 주 최종 적용·검증

- 기능 커밋 712772366e38daa42d41b2cd83f196280a3b7ea2를 dev에 push했다. 실제 Actions https://github.com/MinQDU014/idea-support-server/actions/runs/42836332717 의 검사·테스트와 이미지 게시·배포 작업이 모두 성공했다(최종 attempt 2).
- 첫 실행에서는 배포 수신기의 health 성공 후, 검증자가 동시에 보낸 수동 이전 버전 복구 요청과 CI의 추가 외부 health 요청이 겹쳐 502가 났다. 요청을 분리하고 실패한 게시·배포 작업만 재실행했다. 테스트 성공 작업은 재실행하지 않았다. 서비스 자체의 실패 복구 시험과 이 검증 순서 문제를 구분한다.
- 최종 latest와 dev-712772366e38daa42d41b2cd83f196280a3b7ea2의 manifest digest는 sha256:a6a983ca5926d7161419df187781b01d4af88b55465d545064a9e83356fe8b25 이며 실제 예시 Compose의 image와 일치한다. amd64·arm64가 모두 있다. 외부 예시 health는 status=ok, database=up, seedReady=true다.
- 학생용 request-deploy.py로 기존 예시 커밋 태그를 요청해 실제 이전 이미지 교체를 확인했고, 이후 CI가 새 이미지를 정상 배포했다. SSH 없이 토큰 파일과 Python 3으로 자기 팀 복구를 요청할 수 있다. 다른 팀 경로·latest·임의 명령 문자열은 허용하지 않는다.
- 외부에서 공인 IP의 3306·9001·18080·18088 접근이 불가능함을 확인했다. 최종 controller 설치를 다시 실행해 9개 앱의 상태와 설정 유지, 서비스 활성화를 확인했다. 관리자 복구 스크립트는 서버 admin 디렉터리에 보관하고 Registry 계정 사본은 root 전용 경로로 옮겼다.
- 실제 cd-access.json 두 사본의 Windows 권한도 소유자와 SYSTEM으로 제한했다. git check-ignore로 두 비밀 파일이 제외됨을 확인했다. Git에는 가짜 예제와 비밀값 없는 검증 JSON만 올린다.
- 지정된 11주차 Notion 페이지의 CD 설명과 활동 STEP 1~4, GitHub Variables/Secrets, latest+커밋/digest, Compose 메모리·loopback 포트, health·DB 유지·복구, 다음 주 예고를 수정했다. 새로고침 후 저장된 설정·코드를 확인했다. main/EKS는 다음 주이며 이번 주 생성하지 않음을 명시했다.
- 실제 Swagger UI가 HTTPS 예시 경로와 올바른 API 서버 URL로 로딩됨을 브라우저에서 확인했다. 노션·Swagger 화면 증거는 로컬 .local/evidence/에 보관했다. 실제 연결 기기 설치 검사는 사용자 지시대로 생략했다.
- actionlint, Python 구문 검사, Linux의 배포 보호 동작 단위 검증 2개, Git 공백 검사를 통과했다. DB 권한은 18개 사용자, HTTPS health·Swagger는 9개 앱에서 검증했다. 부하 시험·실패 이미지 자동 복구의 실제 운영 시험·외부 백업 복원은 수행하지 않았다.
- 이후 안내·도구·검증 기록 커밋은 [skip ci]로 같은 앱 빌드를 반복하지 않는다. 기존 deploy/dev-registry/index.html의 로컬 포맷 변경은 미커밋으로 보존했다.

최종 업데이트 위치: GitHub dev 브랜치, 각 팀 GitHub dev Environment, 지정 11주차 Notion 페이지, 서버 /opt/classroom-cd/. 학생 저장소가 정해지면 해당 저장소에 workflow와 자기 팀의 Variables/Secrets만 등록한다. EKS 생성은 다음 주에 진행한다.

### 백업 무결성 검사 보완

- 최종 gzip 무결성 검사에서 초기 백업이 실제 압축 형식이 아님을 발견했다. subprocess가 GzipFile의 파일 디스크립터에 직접 쓰면 Python 압축 경로를 거치지 않는 것이 원인이었다.
- mysqldump의 stdout을 Python 파이프로 받아 gzip writer에 스트리밍하고 CRC 검증을 통과한 뒤 확정 파일로 저장하도록 수정·실제 적용했다. 초기 잘못된 파일은 root 전용 경로에서 .invalid로 구분했다.
- 새 백업 20261110T145517Z.sql.gz(345691 bytes)는 gzip 무결성 검사와 18개 DB 포함 검사를 통과했다. 배포·DB 방화벽·백업 타이머 3개도 모두 active다. 복원 시험을 했다는 의미는 아니다. 비밀값 없는 결과는 docs/evidence/classroom-cd/maintenance-verification.json에 기록했다.

## 2026-11-11 리전·Lightsail 상품 설명 및 관리자 SSH 안내

- 사용자가 시드니 리전을 지적하고 서울이라고 정정했다. provision-lightsail.py의 REGION=ap-southeast-2와 실제 서버 위치가 일치함을 확인했다. 기존 ECR·Registry의 리전 설정을 재사용한 판단이 원인이며 사용자가 시드니를 지정한 것으로 해석하지 않는다. 서울 리전은 ap-northeast-2다. 현재 서버 이전·삭제·새 유료 자원 생성은 수행하지 않았다.
- 사용자가 Containers·Databases 메뉴 사용 여부를 질문했다. 실제 구현은 Lightsail Instances 한 대 안의 Docker Compose 앱·MySQL이며 해당 관리형 서비스는 생성하지 않았음을 설명했다. VM의 Docker 컨테이너와 Lightsail Container Service를 구분한다. 관리형 전환은 아직 지시·적용하지 않았다.
- 사용자가 브라우저 Connect using SSH와 외부 SSH 접속 방법을 요청했다. docs/LIGHTSAIL_SSH_ACCESS.md에 콘솔 경로, Allow Lightsail browser SSH/RDP의 위치, 현재 PowerShell 관리자 키·고정 IP 명령, 상태 확인·접속 오류를 정리하고 운영 README에서 연결했다.
- 실제 현재 관리자 키와 저장된 서버 공개 키를 사용한 외부 SSH에서 hostname·uptime·배포 서비스 active를 확인했다. 로컬 개인 키 내용은 읽거나 출력하지 않았다. 저장된 ED25519 서버 공개 키 지문도 확인했다.
- 브라우저 SSH는 이전 승인 작업 후 닫았던 상태를 기준으로 안내했으며 이번에는 방화벽을 변경하거나 브라우저 SSH 경로를 새로 열지 않았다. 학생에게 관리자 키를 공유하거나 학생 계정을 만들지 않았다.
- 문서만 변경하므로 앱 테스트·이미지 빌드는 반복하지 않는다. 기존 deploy/dev-registry/index.html의 미커밋 포맷 변경을 보존하고 안내 문서만 [skip ci] 커밋으로 기록한다.

업데이트 위치: docs/LIGHTSAIL_SSH_ACCESS.md, deploy/classroom-cd/README.md, Lightsail Networking의 SSH 규칙. 서울 이전을 진행할 때 새 IP·호스트 키·DNS와 리전별 설정을 함께 갱신해야 한다.

## 2026-11-11 서울 이전 요청·예비 백업·계정 제한 확인

- 사용자가 앱·DB·8팀 설정을 보존해 서울로 이전하고 새 고정 IP를 전달한 뒤, DNS 전환 확인 후 시드니 서버를 정리하도록 명시했다. 현재까지 새 서버 생성·DNS 변경·시드니 정리는 수행하지 않았다.
- 서울 CloudShell을 열었으나 AWS 자체 화면에서 프로젝트가 시드니 ap-southeast-2에 할당돼 있고 다른 리전 사용에는 Paid plan 전환 후 고급 기능 활성화가 필요하다는 안내가 나왔다. 공식 프로젝트 리전 문서에서도 새 가입 방식의 지역 고정을 확인했다. 일반 계정의 리전 opt-in과 구분한다.
- 계정 전환 화면은 업그레이드를 먼저 요구하며, 고급 기능 활성화 시 지출 한도가 삭제되고 되돌릴 수 없다고 명시한다. 계정 설정 변경은 수행하지 않았고 소유자가 직접 진행할 수 있도록 해당 화면을 열어 두었다. 사용자의 서울 이전 요청을 임의의 결제 조건 변경이나 새 관리 계정 생성 승인으로 확대하지 않는다.
- prepare-migration.py로 운영 중 MySQL 18개 DB의 논리 백업, 예시+8팀 앱의 현재 digest·환경 설정, 팀별 비밀값·배포 토큰·인증서·Registry 인증 정보를 비공개 보관본으로 만들었다. 로컬 사본 해시가 일치하고 앱 9개·DB 18개·팀별 토큰 9개 포함을 확인했다. 실제 비밀값을 출력하거나 Git에 올리지 않았다.
- 예비 보관본은 로컬 .local/seoul-migration/classroom-state.tar.gz에 있으며 소유자·SYSTEM 접근만 허용한다. 소스는 계속 운영하므로 이 파일이 최종 전환 백업이라는 뜻은 아니다. 실제 cutover 전 쓰기를 잠시 막고 최신 DB를 다시 동기화해야 한다.
- provision-lightsail.py는 리전을 필수 인자로 받고 --plan-only로 생성 전 확인하도록 수정했다. 상태 파일도 리전별로 분리하고 초기 관리자 공개 키 등록은 기존 AWS 관리 키를 보존하도록 바꿨다. 서울 접근이 막힌 상태에서 다른 계정이나 리전으로 우회 생성하지 않았다.
- 서울 이전 안내 문서와 README·SSH 안내를 갱신하고 다음 주 EKS 시드니 초안을 서울에 그대로 적용하지 않도록 표시했다. Python 구문 검사·CLI help·Git 공백 검사를 수행했다. 문서·사전 준비 코드만 [skip ci]로 기록하며 기존 HTML 변경은 보존한다.
- 비밀값 없는 결과: docs/evidence/classroom-cd/seoul-migration-preparation.json. 화면 증거는 로컬 .local/evidence/seoul-region-unavailable.png 및 aws-advanced-activation-review.png에 저장했다.

다음 단계: 사용자가 계정의 서울 사용 제한을 해제하거나 서울 사용 가능한 다른 계정을 지정하면 동일 사양·설정으로 복원한다. 새 IP의 TLS·9개 앱·DB 격리·설정 일치를 확인하고 사용자 DNS 변경 이후 실서비스 검증을 마친 뒤 시드니 Lightsail만 정리한다. 기존 Registry EC2·ECR과 다음 주 EKS 구축은 별도 범위다.

## 2026-11-11 서울 이전 취소·시드니 유지

- 사용자가 계정 전환 요청에 ‘그럼 그냥 두자’라고 답해 서울 이전과 그에 따른 시드니 정리 요청을 취소했다. 현재 시드니 VM·IP·도메인·8팀 앱·DB를 유지한다. 예비 백업은 보관하며, 다시 명시적으로 요청하기 전에는 이전·업그레이드·삭제를 재개하지 않는다.
- ‘호주는 왜 무료인가’에 대해 AWS 공식 프로젝트 리전·Free plan 문서를 다시 확인했다. 호주 지역 자체가 무료인 것이 아니라 신규 가입 방식이 한국을 시드니 프로젝트에 배정하고, Free plan의 크레딧·이용 기간이 현재 사용을 지원하는 구조다. 서울 리전의 일반 요금과 무료 플랜 제한을 구분한다.
- Free plan은 최대 6개월 또는 크레딧 소진 중 먼저 도래한 시점에 종료하며, 유료 전환 없이 자동 무제한 운영되는 무료 서버로 설명하지 않는다. 크레딧 잔액·정확한 만료일은 이번 조회에서 확인하지 않았다.
- 이전 검토 문서·운영 README·SSH 안내·다음 주 EKS 초안의 현재 상태를 사용자 최신 결정으로 갱신했다. AWS 결제·계정·리소스·DNS 설정은 변경하지 않는다. 문서 변경만 [skip ci]로 기록하고 기존 HTML 미커밋 변경은 보존한다.

업데이트 위치: 현재 운영 안내는 deploy/classroom-cd/README.md, 이전 취소 기록은 docs/LIGHTSAIL_SEOUL_MIGRATION.md. 현재 사용량·크레딧·무료 플랜 종료일은 AWS 청구 화면에서 확인한다.
