# 11주차 CD 학습 구성 검토

2026-11-10 확정·실행: **이번 주 dev는 Lightsail VM + Docker Compose**, **다음 주 main은 공유 EKS**다. 사용자 최종 지시로 EKS 생성은 다음 주로 미뤘다. 아래 비교는 설계 배경이며 실제 운영·학생 설정·검증은 [공유 CD 안내](../deploy/classroom-cd/README.md)를 따른다. Lightsail에는 예시와 8팀 앱, 팀별 DB를 설치했으며 EKS는 생성하지 않았다.

## 권장 구성

오늘은 dev에서 공유 실행 서버 한 대와 Docker Compose로 배포·상태 확인·실패 진단·되돌리기를 학습한다. main은 이후 ECR → EKS로 연결해 같은 문제를 Kubernetes가 어떻게 처리하는지 비교한다. Swarm은 선택 시연으로 둔다.

EC2와 Lightsail은 서버를 제공하는 상품이고 Compose와 Swarm은 그 서버에서 컨테이너를 운영하는 방식이다. EC2 + Compose, EC2 + Swarm, Lightsail + Compose, Lightsail + Swarm 모두 가능한 조합이다. Lightsail 자체가 CD를 대신하지는 않는다.

| 구분 | dev | main |
| --- | --- | --- |
| 이미지 저장 | 기존 `docker.minq.live/teamN/idea-support-server` | 기존 ECR 팀별 이미지 |
| 실행 환경 | 공유 Lightsail VM 한 대 + Docker Compose (이번 주) | 공유 EKS 클러스터 한 개 (다음 주 예정) |
| 팀 구분 | Compose 프로젝트 `team1`~`team8`, 팀별 라우팅·설정·볼륨 | namespace `team1`~`team8`, 팀별 권한·자원 한도 |
| 최신 이미지 | `latest` 유지 | 최신 별칭과 커밋 태그·digest 병행 |
| 정확한 배포·되돌리기 | 해당 CI 실행의 커밋 태그 또는 digest 기록 | 해당 CI 실행의 커밋 태그 또는 digest 기록 |
| 학습 중심 | 서버·포트·환경변수·DB·볼륨·로그·배포 순서 | Deployment·Service·readiness·복제·순차 교체·권한 |

위 구조는 수업에서 직접 관리하는 서버와 관리형 Kubernetes의 차이를 비교하기 위한 것이다. 실제 서비스에서 dev와 main에 서로 다른 실행 플랫폼을 반드시 써야 한다는 뜻은 아니다. 환경 차이가 늘면 설정과 검증 부담도 늘어난다.

## 서버와 8팀 구성

- 현재 Registry 서버는 t3.micro, RAM 1GiB다. 작은 이미지 저장소 검증 결과를 Spring Boot 앱 8개·DB의 동시 실행 능력으로 확대 해석하지 않는다.
- 권장안은 Registry 서버를 유지하고 dev 실행용 공유 서버 한 대를 별도로 두는 것이다. 팀마다 EC2를 만들지 않는다. 비용을 더 줄이기 위한 합치는 구성은 사양 증설·공동 장애 영향을 따로 검토한다.
- Compose 프로젝트 이름과 도메인 또는 포트를 팀별로 나눈다. `container_name`과 호스트 포트는 공통 고정값으로 복사하지 않는다. 한 팀 배포가 다른 팀의 컨테이너를 내리지 않도록 프로젝트명을 명령에 고정한다.
- DB 비용·메모리를 줄이려면 dev MySQL 한 개에 팀별 스키마·사용자를 만들고 각 사용자에게 자기 스키마 권한만 준다. 팀별 DB 데이터와 비밀값을 분리한다. 앱 이미지를 바꿀 때 DB 볼륨을 삭제하지 않는다.
- 순차 실습으로 시작하면 작은 실행 서버부터 측정할 수 있다. 8팀 동시 실행에는 JVM·DB·교체 중 구버전과 새 버전의 동시 메모리까지 측정해 사양을 정한다. 4GiB나 8GiB를 충분하다고 단정하지 않는다.
- 학생은 이전 결정대로 EC2에 직접 로그인하지 않아도 된다. 먼저 강사 터미널에서 배포를 시연하고 학생은 팀별 GitHub 코드·이미지·접속 결과를 확인한다. 자동 CD를 추가할 때 팀 경로와 허용 배포 작업으로 제한한 실행 경로를 설계한다.
- EKS도 팀별 클러스터 8개 대신 한 클러스터에 namespace 8개를 만든다. namespace 이름만으로 권한·네트워크가 자동 격리되지는 않는다. RBAC, requests/limits, ResourceQuota를 함께 설정하며 네트워크 분리가 필요하면 이를 지원하는 CNI와 NetworkPolicy를 검증한다.

## 오늘의 실습 순서

1. Registry에 이미지가 저장된 것과 앱이 실행된 것을 구분한다.
2. 강사 터미널에서 팀 이미지 `latest`를 가져와 Compose로 실행한다. DB 연결값·비밀값은 서버에 주입한다.
3. 팀 URL과 `/common/health`, 컨테이너 로그를 확인한다. DB 데이터가 어디에 보관되는지 확인한다.
4. 응답에 보이는 버전 등 작은 변경을 dev에 push하고 CI 완료를 확인한다.
5. 새 이미지를 받아 앱 컨테이너를 교체한다. 단순 Compose 교체 중 짧은 중단이 생길 수 있음을 보여준다.
6. 잘못된 DB 설정 또는 실패하는 앱 버전을 배포해 로그와 상태로 원인을 찾는다.
7. GitHub dev의 변경 이력에서 문제를 만든 일반 커밋을 찾고 `git revert`로 취소하는 새 커밋을 만들어 dev에 push한다. 기존 Actions의 검사·이미지 생성·앱 교체·health를 다시 확인하고 실제 기능에서 문제 변경이 취소됐는지 본다. GitHub에서 합친 PR은 해당 PR의 Revert로 복구 PR을 만들어 dev에 merge할 수 있다.
8. 새 Revert 커밋 번호의 태그와 digest를 배포 기록에 남긴다. 이번 주 복구 실습은 Git과 자동 CD로 진행하고 Python 보조 도구·서버 수동 교체를 요구하지 않는다. 코드 복구가 DB 스키마·데이터 복구를 뜻하지는 않는다.

`latest`는 최신 업로드를 찾는 이름으로 계속 쓴다. 실행 버전은 같은 실행의 커밋 태그·digest로 기록한다. Revert 후에는 복구 커밋을 새로 빌드해 새 태그·digest로 배포하므로 예전 이미지의 digest와 같다고 가정하지 않는다.

## Swarm을 넣는 경우

Swarm mode는 Docker Engine에 포함되어 있어 별도 오케스트레이터 패키지를 설치하는 방식과 다르다. 서비스의 원하는 복제 수 유지, 서비스 업데이트·롤백, 다중 호스트 네트워크를 학습할 수 있다.

단일 노드에서도 서비스 운영 개념은 시연할 수 있지만 서버 한 대의 장애를 견디는 구성이 되지는 않는다. main의 최종 목표가 EKS라면 Swarm 명령과 Kubernetes 리소스를 모두 필수 실습으로 넣는 대신, 기본 Compose 배포를 마친 뒤 선택 비교로 다루는 것을 권장한다. Swarm 운영 자체가 학습 목표이면 dev를 Swarm으로 선택할 수 있다.

## EC2와 Lightsail, 비용 판단

EC2를 택하면 VPC·보안 그룹·디스크·권한 같은 AWS 기본 구성까지 EKS와 연결해 설명하기 쉽다. Lightsail을 택해도 Ubuntu 위에서 Docker·Compose를 직접 운영하는 CD 학습은 가능하다. 고정 요금과 설정 단순화가 우선이면 Lightsail VM은 좋은 대안이다. 학습 차이는 서버 관리 상품 쪽이며 앱 배포의 핵심 흐름은 같다.

2026-11-10 확인한 공식 가격표의 Linux/Unix 일반형 공인 IPv4 포함 Lightsail VM은 4GB USD 24/월, 8GB USD 44/월이다. 디스크·약정 범위의 전송량 등이 포함된 묶음이며 추가 사용량·세금과 실제 선택 리전 조건은 별도 확인한다. 여기서 말하는 것은 Lightsail VM이고 Lightsail Container Service가 아니다.

EKS 표준 지원 버전의 기본 클러스터 요금은 USD 0.10/시간, 730시간이면 USD 73/월이다. 노드·디스크·공인 IP·로드 밸런서·NAT·DB 등의 비용은 별도다. 확장 지원 요금은 더 높다. 학생 8팀은 클러스터 한 개를 공유하고 수업에 필요한 시간만 생성·사용·정리하는 방식을 권장한다. 노드만 0개로 줄여도 클러스터 요금은 남는다.

## 이번에 반영한 Notion 후반부

브라우저로 [11주차 CD 강의](https://app.notion.com/p/project-2026-01/11-CD-40d9fa2a819d801ebbbbf605cc00843f)를 수정하고 새로고침 후 저장을 확인했다. Notion connector에서는 404여서 로그인된 브라우저를 사용했다. dev 실제 주소·Compose·DB 분리·GitHub Variables/Secrets·자동 배포·상태 확인·SSH 없는 복구를 반영했다. main/EKS는 다음 주 예고로 구분하고 아직 생성하지 않았음을 명시했다. 수동 서버 명령은 강사 시연으로, 학생 작업은 GitHub와 자기 팀 URL로 분리했다.

- 6장: 기존 main 중심 흐름을 dev → 자체 Registry → 공유 실행 서버, main → ECR → EKS 두 경로로 나눈다.
- 6장: 기존 `docker-repo.minq.work`를 현재 `docker.minq.live`로 바꾼다.
- 6장: 온프레미스의 실행 방식으로 Docker Compose도 포함한다. Registry에 이미지를 올리는 것만으로 서버가 자동 교체되는 것은 아니며 별도 배포 실행 단계가 필요함을 유지한다.
- 6장: DNS와 reverse proxy를 별도 행으로 구분한다. 현재 도메인의 DNS는 도메인 제공자에서 설정하고 Caddy·Nginx는 HTTP 요청을 전달하는 역할이다.
- 7장: 현재 CI가 이미 최신 별칭과 커밋별 태그를 함께 남기므로, 수업도 그 이미지로 실제 되돌리기를 연습하도록 바꾼다.
- 7장: 상태 확인이나 자동 롤백은 도구 이름만으로 보장되지 않는다. readiness·업데이트 정책·실패 처리 단계를 구체적으로 제시한다. Kubernetes의 실패한 rollout을 확인하고 되돌리는 절차도 별도 학습한다.
- 8장: 서비스 상품의 나열보다 단일 서버에서 생긴 문제를 EKS가 어떻게 다루는지 비교하는 질문으로 연결한다.

## 근거와 업데이트 위치

- [Docker: 단일 서버 Compose 운영](https://docs.docker.com/compose/how-tos/production/)
- [Docker: Swarm mode 기능과 적용 범위](https://docs.docker.com/engine/swarm/)
- [Docker: Swarm manager와 장애 허용](https://docs.docker.com/engine/swarm/admin_guide/)
- [AWS Lightsail 가격](https://aws.amazon.com/lightsail/pricing/)
- [AWS EKS 가격](https://aws.amazon.com/eks/pricing/)
- [Kubernetes: 다중 팀 권한·자원·네트워크 분리](https://kubernetes.io/docs/concepts/security/multi-tenancy/)
- [Kubernetes: Deployment 진행 상태와 되돌리기](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

완료한 업데이트: 11주차 Notion의 CD 설명·6·7·8장·활동 STEP 1~4·마무리·다음 주 예고, dev 공유 Compose·인증된 배포 API·CI 배포/health 단계. main workflow는 기존 ECR 업로드를 유지하며 EKS 리소스·권한·배포 검증은 다음 주 작업이다.
