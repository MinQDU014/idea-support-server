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
