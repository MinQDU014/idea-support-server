# 11주차 공유 CD 환경

2026-11-10 사용자 확정: dev는 **Lightsail VM 한 대 + Docker Compose**, main은 **EKS 클러스터 한 개**를 8팀이 공유한다. Lightsail VM은 서버리스가 아니며 OS·Docker·MySQL을 직접 관리한다.

기존 EC2 Registry `docker.minq.live`는 유지한다. 최신 이미지 태그는 `latest`, 특정 배포·복구에는 커밋 태그 또는 digest를 쓴다. MySQL은 한 인스턴스를 공유하고 팀별 DB·사용자를 분리하며 dev와 main의 DB도 나눈다.

## 진행 상태

- 강의용 AWS 계정은 `950177940921`, 리전은 `ap-southeast-2`다. 로컬 기본 AWS 프로필은 다른 계정이므로 이 환경을 생성하는 데 사용하지 않는다.
- 로그인된 강의용 계정의 CloudShell 접근을 확인했다. Lightsail 고정 IP를 확보하면 사용자에게 전달하고 도메인 등록을 기다리며 서버 설치를 계속한다.
- 구성이 적용된 뒤 이 문서와 `docs/DEV_REGISTRY_WORK_LOG.md`에 실제 주소·검증 결과를 갱신한다. 아직 생성·실행 성공으로 간주하지 않는다.

## 업데이트 위치

인프라·설치·배포 도구는 이 디렉터리, CI/CD는 `.github/workflows/`, 강의는 11주차 Notion 페이지, 실제 비밀번호는 Git에서 제외한 로컬 파일과 서버 전용 파일에 보관한다.
