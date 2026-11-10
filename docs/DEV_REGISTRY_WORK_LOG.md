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
- GitHub Actions 실제 실행과 앱 이미지 업로드 결과는 후속 확인 후 기록한다. 기기 설치·연결 검증은 사용자 지시에 따라 생략한다.

## 업데이트 위치

- CI: `.github/workflows/dev-registry.yaml`, GitHub `dev` Environment.
- 서버·화면: `deploy/dev-registry/`, EC2 `/opt/classroom-registry/compose.json`·`Caddyfile`.
- 이미지: EC2 `/data/registry`, 인증서: `/data/caddy`.
- 강의: `docs/DEV_REGISTRY.md`와 10주차 CI Notion 페이지.
- 월 비용 추정: USD 17.126 + 전송량·세금 등, 크레딧 적용 전. 정지 후에도 디스크·고정 IP 비용은 남으며 종료 시 보존한 디스크도 따로 정리한다.
