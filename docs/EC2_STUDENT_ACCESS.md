# 학생 접속 방식

2026-11-10 최종 결정: **학생은 EC2에 SSH·SSM으로 접속하지 않는다.** 각 팀 GitHub의 dev 브랜치에서 `https://docker.minq.live`로 이미지를 업로드한다.

학생은 [Registry 업로드 안내](DEV_REGISTRY.md)에 따라 팀 번호와 GitHub Secrets만 설정한다. 별도 학생 AWS 계정·SSH 키·Bastion은 준비하지 않는다. 서버의 SSH는 기존 관리자용으로 유지한다.

팀 번호가 없는 `team/idea-support-server`는 강의 예시이고, 학생은 `team1/idea-support-server`~`team8/idea-support-server`를 사용한다. 이미지 업로드는 앱 실행과 별도이며, CD에서 동일한 이미지 주소를 가져와 실행한다.

업데이트 위치: 학생 안내는 `docs/DEV_REGISTRY.md`, CI는 `.github/workflows/dev-registry.yaml`, 실제 계정은 Git에 제외한 루트 `team-access.json`과 각 팀의 GitHub `dev` Environment Secrets다.
