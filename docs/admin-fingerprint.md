# 관리자 지문 인증

대상은 터미널의 `sudo` / `sudo -i`와 설치·설정 창의 polkit 인증이다. 각 인증에서 지문을 먼저 1회 확인하며, 지문이 일치하지 않거나 약 10초 동안 손가락을 대지 않으면 기존 비밀번호 인증으로 이어진다. 다음 인증부터 적용되며 재로그인이나 서비스 재시작이 필요하지 않다.

## 적용과 원복

지문 드라이버가 정상이고 해당 사용자의 지문이 등록되어 있어야 한다. 이 도구는 Ubuntu 26.04의 PAM 구성을 검증 대상으로 한다. 현재 사용자의 터미널에서 실행한다.

```bash
./admin-fingerprint status
./admin-fingerprint install --dry-run
./admin-fingerprint install
```

원복은 다음과 같다. 백업 접근에는 관리자 권한이 필요하므로 dry-run도 인증 창을 띄울 수 있다.

```bash
./admin-fingerprint rollback --dry-run
./admin-fingerprint rollback
```

원본 PAM 파일, 전후 해시, 독립 실행 가능한 복구 스크립트는 `/var/lib/ubuntu-custom/admin-fingerprint/<백업ID>/`에 root 전용으로 보관한다. 사용자 저장소가 없어져도 아래 방식으로 복구할 수 있다.

```bash
sudo /usr/bin/python3 /var/lib/ubuntu-custom/admin-fingerprint/백업ID/restore.py rollback
```

백업 이후 다른 관리자가 PAM 파일을 변경했다면 원복이 이를 덮어쓰지 않고 중단한다. 원복은 지문 센서 드라이버나 등록된 지문을 삭제하지 않는다.

## 설정 방식

- `/etc/pam.d/sudo`, `/etc/pam.d/sudo-i`: 기존 `common-auth` 앞에 `auth sufficient pam_fprintd.so max-tries=1 timeout=10`을 추가한다. 계정·세션 처리와 비밀번호 fallback을 유지한다.
- `/etc/pam.d/polkit-1`: 지문 인증 이후에는 `/usr/lib/pam.d/polkit-1`의 배포판 정책을 auth/account/password/session별로 포함한다. [Linux-PAM의 절대 경로 include 처리](https://github.com/linux-pam/linux-pam/blob/v1.7.0/libpam/pam_handlers.c#L291)를 사용한다.
- `common-auth`, GDM 잠금 화면, SSH 설정은 수정하지 않는다.
- 적용 중 PAM 정책 로드와 계정 검사가 실패하면 세 파일을 직전 상태로 복구한다.

PAM의 인증은 순서대로 진행되므로 이 구성에서는 지문 확인 중 비밀번호를 동시에 처리하지 않는다. 비밀번호를 쓰려면 지문 단계가 끝날 때까지 약 10초 기다린다. `sudo` 인증이 이미 캐시되어 있으면 지문을 다시 묻지 않을 수 있다. [pam_fprintd 매뉴얼](https://manpages.ubuntu.com/manpages/resolute/man8/pam_fprintd.8.html)

## 확인 방법

```bash
# 기존 sudo 캐시를 사용하지 않고 실제 인증 확인
sudo -k -v
# 별도 PAM 서비스인 sudo-i 확인
sudo -k -i /usr/bin/id -u
```

안내가 나타나면 등록한 오른쪽 검지를 센서에 댄다. GUI 인증은 `pkexec /usr/bin/id -u` 같은 관리자 인증 요청으로 확인할 수 있다. 약 10초간 지문을 대지 않았을 때 비밀번호 입력으로 넘어가는지도 확인한다.

패키지 업그레이드 후 `./admin-fingerprint status`로 설정을 확인한다. sudo 설정 파일을 배포판 원본으로 교체했다면 재적용할 수 있다. polkit은 배포판 파일을 포함하므로 해당 경로가 유지되는 한 후속 정책을 사용한다. 다른 PAM 확장이나 다른 Ubuntu 릴리스가 도입되면 기존 인증 흐름을 먼저 검토한다.

## 실제 검증과 센서 오류 복구

2026-09-19 적용 후 실제 오른쪽 검지로 sudo와 sudo-i를 인증했고, polkit 관리자 인증도 통과했다. 지문을 감지하지 못하면 약 10초 뒤 비밀번호 입력으로 넘어가는 것을 확인했다. 비밀번호를 직접 입력하는 성공 시험은 별도로 하지 않았다.

시험 중 시간 초과 뒤 재시도에서 기존 비공식 드라이버가 장치 응답 오류를 한 번 반환했다. fprintd 재시작 이후 위 세 방식 모두 성공했다. 같은 현상이 재발하면 지문 단계를 기다린 뒤 비밀번호로 아래 명령을 실행할 수 있다.

```bash
sudo systemctl restart fprintd.service
```

서비스 재시작은 등록된 지문을 지우지 않는다. 현재 지문을 읽는 작업이 진행 중일 때는 먼저 인증창을 닫고 실행한다. 반복되면 센서 드라이버의 시간 초과/취소 처리를 추가로 점검할 대상이다. 이번 PAM 설정 변경에는 센서 드라이버 코드 수정이 포함되지 않았다.

이 설정은 GNOME 크래시 수정과 별개다. 아직 이전 Mutter가 실행 중이라면 그 패치 활성화에는 별도로 재로그인이 필요하다.
