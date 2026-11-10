# EC2의 공유 dev Registry

최종 구성은 **EC2 t3.micro 한 대 + Registry 한 개 + Caddy 한 개**, 암호화한 gp3 40GiB다. 번호 없는 `team/idea-support-server`는 강의 예시이며 학생은 `team1/idea-support-server`~`team8/idea-support-server`를 사용한다. 학생은 EC2 접속 없이 각 팀 GitHub의 dev CI로 이미지를 업로드한다.

## 현재 서버

- 계정 `950177940921`, 시드니 `ap-southeast-2`.
- 고정 IP `52.65.110.152`.
- SSH는 생성 시 지정한 관리자 IP `/32`에만 허용한다. EC2에 AWS IAM 역할은 추가하지 않았다.
- 이미지: 설치 시 공식 `registry:3`와 `caddy:2-alpine`을 내려받아 실제 digest로 고정한다. 재실행 시 기존 digest를 유지한다.
- 저장 데이터: `/data/registry`.
- 실행 설정: `/opt/classroom-registry/compose.json`, `Caddyfile`.
- 현재 `https://docker.minq.live`의 HTTPS 443으로 운영한다. Caddy가 TLS-ALPN-01로 인증서를 발급·갱신하므로 공인 HTTP 80은 열지 않는다.
- Registry API 5000은 컨테이너 내부에서만 사용한다. 이미지 삭제 API는 비활성화한다.

## 계정과 데이터

`team1`~`team8` 로그인 계정을 발급했다. 자격 증명은 서버의 `/opt/classroom-registry/team-access.json`에 root 전용 권한으로 보관한다. 설치 재실행은 기존 계정을 유지한다. 모든 사용자가 모든 팀 이미지에 접근할 수 있으며 경로별 권한 분리는 하지 않는다.

강사의 백엔드 로컬 복사본은 루트 `team-access.json`이며 `.gitignore`로 제외한다. GitHub에는 가짜 값만 넣은 `team-access.example.json`을 올린다. CI는 로컬 파일 대신 각 팀 `dev` Environment의 Secrets를 사용한다. 로그인 계정과 이미지 namespace는 별개이므로 예시 `team` 경로에 별도 로그인 계정을 새로 만들 필요는 없다.

학급 밖의 신뢰하지 않는 팀끼리 사용하는 구성이 아니다. 별도 권한이 필요해지면 token auth 또는 Harbor 같은 관리 기능을 검토한다.

## 설치와 HTTPS 적용

`cloudformation.yaml`은 서버 한 대·고정 IP·관리용 공개 키·보안 그룹을 생성한다. Ubuntu 24.04와 Docker를 준비한다. 개인 키는 로컬 `.local`에만 보관한다.

EC2에 `install-registry.py`, `index.html`, `verify-registry.py`를 같은 폴더로 전송한다.

```bash
sudo python3 install-registry.py
```

도메인을 고정 IP로 연결한 뒤 다음처럼 다시 실행한다. 이미지 데이터와 계정은 유지되며 신뢰할 수 있는 인증서를 자동 발급·갱신한다.

```bash
sudo python3 install-registry.py --hostname docker.minq.live
```

초기 HTTP 준비 상태에서만 아래 SSH 터널을 사용할 수 있다. 현재 운영은 HTTPS이므로 이 터널을 사용하지 않는다.

```bash
ssh -i classroom-registry -L 18080:127.0.0.1:8080 ubuntu@52.65.110.152
```

## 검증

```bash
sudo python3 verify-registry.py \
  --url http://127.0.0.1:8080 \
  --access-file /opt/classroom-registry/team-access.json \
  --output /tmp/registry-verification.json
```

인증 요구·잘못된 비밀번호 거절·UI 응답·8개 팀의 동시 2MiB OCI 레이어 업로드와 manifest 읽기를 확인한다. `team1` 계정으로 `team2` 이미지를 읽을 수 있다는 공유 접근 특성도 검사한다. 검증 이미지는 `teamN/registry-smoke:verify-*`이며 앱 이미지가 아니다. 실제 앱 8개 동시 업로드 부하를 보장하는 성능 시험은 아니다.

## 비용과 정리

2026-11-10 AWS Price List의 시드니 단가로 EC2 시간당 USD 0.0132, gp3 GB·월당 USD 0.096이다. 730시간, 디스크 40GB, IPv4 시간당 USD 0.005를 적용하면 월 USD 17.126 + 전송량·세금 등이다. 무료 크레딧 적용 전 추정이며 청구 상한이 아니다.

CPU 크레딧은 Standard로 설정한다. 오래 부하를 주면 크레딧 소진으로 성능이 제한될 수 있다. Registry 메모리 상한 256MiB, Caddy 96MiB이며 Docker 빌드는 EC2에서 하지 않고 GitHub Actions에서 한다.

팀별 저장 한도·자동 retention·자동 garbage collection은 없다. 공유 디스크 여유 공간을 확인한다. 인스턴스를 정지해도 디스크와 고정 IP 비용은 남는다. 종료 시 디스크를 보존하도록 했으므로 마지막에는 남은 디스크와 고정 IP도 확인해 정리한다.

## 업데이트 위치

- 서버 사양·방화벽: `cloudformation.yaml`.
- Registry·인증·HTTPS: `install-registry.py`, 실제 서버의 `compose.json`·`Caddyfile`.
- 화면: `index.html`.
- 검증: `verify-registry.py`와 작업 기록.
- 각 팀 CI: `.github/workflows/dev-registry.yaml`와 GitHub `dev` Environment.
