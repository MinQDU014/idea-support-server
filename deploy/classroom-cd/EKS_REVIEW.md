# main 공유 EKS 생성 구성

2026-11-10. 실제 생성 직전 검토용. 아직 클러스터는 생성하지 않았다.

2026-11-11 최종 결정: 사용자가 계정의 지역 제한을 확인한 뒤 서울 이전을 취소해 현재 시드니 구성을 유지한다. EKS 생성은 다음 주 범위를 유지하며, 아래 초안은 그때 실제 계정·네트워크·요금을 재검증한 후 적용한다.

- 계정 950177940921, 시드니, 클러스터 `classroom-main` 한 개. API에서 표준 지원 중인 1.36을 확인했다.
- 비용 절약을 위해 t3.large(2 CPU·8GB) 워커 한 대, 암호화 gp3 30GB, 표준 CPU 크레딧 모드. 단일 워커이므로 서버 장애를 견디는 고가용성 구성은 아니다. 수업은 한 번에 하나의 배포로 진행한다.
- 8팀 namespace와 번호 없는 예시 namespace에 Deployment·Service·팀별 main DB Secret·RBAC·자원 한도를 둔다. namespace만으로 격리됐다고 표현하지 않는다. 지원하는 VPC CNI 정책을 켜고 다른 팀 통신 차단을 확인한다.
- NAT Gateway와 팀별 Load Balancer는 만들지 않는다. 내부 NLB 한 개와 공통 HTTP gateway를 공유하고 기존 Lightsail HTTPS의 `/main/team1`~`/main/team8`, `/main/example`로 연결한다.
- NLB 전용 사설 subnet 두 개, 인터넷 경로 없는 route table을 만든다. 워커는 기존 공인 subnet에서 이미지를 내려받고 SSH는 개방하지 않는다. NLB는 Lightsail 사설 IP에서 오는 80번만, 노드는 NLB에서 오는 30080번만 허용한다.
- Lightsail과 **같은 리전의 default VPC**를 peering한다. MySQL 3306은 공인 인터넷에 열지 않으며 main 앱은 사설 IP로 팀별 main DB에 연결한다.
- GitHub OIDC 역할은 현재 예시 저장소의 `main` Environment에만 신뢰를 준다. Environment는 main 브랜치만 허용한다. ECR 권한은 예시 repository 하나, Kubernetes 권한은 예시 namespace 하나의 앱 교체·상태 확인으로 한정한다. 실제 학생 저장소가 정해진 뒤 팀별 역할의 신뢰·namespace를 연결한다.
- 관리자 및 CI 접속을 위해 EKS API는 TLS/IAM 인증을 사용하는 공인 endpoint와 사설 endpoint를 함께 사용한다. 익명 앱 API를 여는 것과 구분하며 Kubernetes 관리자 권한은 학생에게 나누지 않는다.
- 기존 Lightsail에서 생성한 **main 전용 DB 접속값과 앱 비밀값**을 AWS CloudShell을 거쳐 해당 namespace의 Kubernetes Secret에 저장한다. 비밀값은 공개 Git·Notion·로그에 쓰지 않는다.

## 비용과 상태

EKS 제어부만 USD 0.10/시간, 730시간이면 USD 73/월이다. 워커·디스크·공인 IP·공통 내부 NLB 등을 더한 **EKS 추가 비용은 월 약 USD 180~200**으로 예산을 잡는다. 사용량·리전별 단가·세금에 따라 달라지며 크레딧 적용 전 예상이다. 기존 Lightsail USD44/월과 Registry 비용은 별도다. 노드를 정지해도 클러스터 요금은 남는다.

현재 강의 계정은 Free plan ACTIVE이며 EKS 목록 조회와 지원 버전 조회가 정상이다. 생성 시 추가 제한이 나오면 유료 플랜 전환을 임의로 하지 않는다. 클러스터는 수업 전후 필요한 시간에 운영하며 종료 시 NLB·클러스터·노드 등 과금 리소스를 함께 정리한다. 학생이 공유 자원을 삭제하지 않는다.

생성 템플릿: `eks-cloudformation.json` (`eks-template.py`로 생성). 이 문서는 실제 생성·배포가 성공했다는 기록이 아니다. 성공 여부와 실제 주소는 검증 후 README와 작업 기록에 추가한다.
