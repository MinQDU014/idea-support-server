# Lightsail 관리자 접속 — 브라우저 SSH와 외부 SSH

2026-11-11. 두 방법 모두 같은 Ubuntu 가상 서버에 접속한다. 이번 환경은 Lightsail **Instances** 안에서 Docker Compose·팀별 앱·MySQL을 실행하며, AWS의 **Containers / Databases** 상품을 생성한 구성이 아니다.

## 현재 서버와 리전

- 인스턴스 `classroom-dev-compose`, 사용자 `ubuntu`, SSH 포트 TCP 22.
- 현재 고정 IP `13.55.177.148`, 앱 도메인 `daelim.minq.live`.
- 실제 위치는 Sydney, `ap-southeast-2a`다. 기존 ECR·Registry와 같은 시드니 리전 값을 재사용한 것이 원인이다. 사용자는 서울을 원한다고 정정했으며 서울 리전은 `ap-northeast-2`다.
- **서울 이전은 아직 수행하지 않았다.** 이 안내의 IP는 현재 시드니 서버의 주소다. 이전 후 새 IP·서버 공개 키·DNS를 갱신해야 한다. 이번 안내 작업에서 기존 서버를 삭제하거나 새 유료 자원을 만들지 않았다.
- 실제 이전 요청 후 AWS 화면에서 이 계정이 시드니에 고정된 새 가입 방식의 프로젝트임을 확인했다. 서울 사용에는 유료 플랜 전환과 고급 기능 활성화가 요구된다. [이전 진행 기록](LIGHTSAIL_SEOUL_MIGRATION.md)을 참고한다.

## 1. 웹브라우저에서 접속

1. AWS Lightsail → **Instances** → `classroom-dev-compose`를 연다.
2. **Connect** 탭 → **Use your browser** → **Connect using SSH**를 누른다.
3. 터미널이 열리면 `ubuntu` 사용자로 Linux 명령을 실행한다. 로컬 개인 키 파일을 선택하거나 업로드할 필요가 없다.

마지막 적용한 방화벽은 **브라우저 SSH 차단**, 외부 SSH는 관리자 IP `59.14.52.80/32` 허용이다. 초기 키 등록 때 잠시 사용한 브라우저 접속 경로를 닫았으므로 브라우저 SSH를 사용할 때는 먼저 다음 설정이 필요하다.

1. 서버의 **Networking** → **IPv4 firewall**에서 **SSH / TCP / 22** 규칙을 수정한다.
2. **Restrict to IP address**와 기존 관리자 IP 제한을 유지한다.
3. **Allow Lightsail browser SSH/RDP**를 체크하고 저장한다.
4. **Connect**로 돌아가 **Connect using SSH**를 누른다.
5. 일회성 시연 후 체크를 다시 해제하면 기존 관리자 IP 전용 설정으로 돌아간다.

브라우저 SSH를 위해 22번을 `Any IPv4 address` 또는 `0.0.0.0/0`에 열 필요는 없다. 이 안내 작업에서 실제 방화벽은 변경하지 않았다.

## 2. 내 컴퓨터의 PowerShell에서 접속

현재 관리자 컴퓨터에는 전용 개인 키가 이미 있다. AWS 콘솔에서 새 키를 다운로드할 필요가 없다. 파일은 백엔드 저장소 밖 `Documents/notion/.local/classroom-cd`에 있고, 서버 공개 키 확인 파일은 같은 폴더의 `cd-known-hosts`다.

현재 컴퓨터의 PowerShell에서 다음을 실행한다.

```powershell
$classroomKey = "$env:USERPROFILE\Documents\notion\.local\classroom-cd"
$classroomKnownHosts = "$env:USERPROFILE\Documents\notion\.local\cd-known-hosts"
ssh -i "$classroomKey" -o IdentitiesOnly=yes -o "UserKnownHostsFile=$classroomKnownHosts" -o StrictHostKeyChecking=yes ubuntu@13.55.177.148
```

이 명령은 저장된 서버 공개 키를 확인하고 관리자 개인 키로 접속한다. 접속 후 다음 명령으로 상태를 확인할 수 있다.

```sh
whoami
hostname
sudo docker ps
sudo systemctl status classroom-deploy --no-pager
exit
```

다른 컴퓨터에서 접속하려면 그 컴퓨터의 공인 IP를 SSH 규칙에 `/32`로 등록하고, 해당 관리자에게 등록된 별도 개인 키를 사용해야 한다. 네트워크가 바뀌면 공인 IP도 바뀔 수 있다. 서버 IP가 아니라 **접속하는 컴퓨터 쪽 공인 IP**를 허용한다.

현재 키와 `ubuntu`의 sudo 권한은 모든 팀의 앱·DB를 관리하는 강사용 권한이다. 학생에게 관리자 키를 공유하지 않는다. 학생은 기존 GitHub dev 배포와 팀별 URL을 사용한다. 학생 SSH 계정은 생성하지 않았다.

## 오류 확인

| 증상 | 먼저 확인할 것 |
| --- | --- |
| 브라우저 SSH 접속 실패 | **Allow Lightsail browser SSH/RDP** 허용 여부 |
| `Connection timed out` | 서버 IP·실행 상태·SSH 22번과 접속 PC의 현재 공인 IP 허용 여부 |
| `Permission denied (publickey)` | 사용자 `ubuntu`와 해당 서버에 등록된 개인 키인지 확인 |
| 서버 키 변경 경고 | 재생성·이전 여부와 새 서버 공개 키 확인. 기존 기록을 무조건 삭제하거나 검증을 끄지 않는다. |

## 공식 안내와 업데이트 위치

- [AWS 브라우저 SSH 접속](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-connect-to-your-instance-virtual-private-server.html)
- [AWS 방화벽과 Allow Lightsail browser SSH/RDP](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-editing-firewall-rules.html)
- [AWS SSH 키와 접속 방식](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-ssh-in-amazon-lightsail.html)

접속 허용 범위는 Lightsail **Networking → SSH 규칙**, 관리자 키는 로컬 `.local/` 및 서버 `authorized_keys`, 앱·DB는 `/opt/classroom-cd/`, 리전·IP·안내는 이 문서와 `deploy/classroom-cd/README.md`에서 갱신한다.
