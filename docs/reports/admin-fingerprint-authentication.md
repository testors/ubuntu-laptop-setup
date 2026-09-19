# 관리자 작업의 지문 인증

날짜: 2026-09-19 (KST)

## 적용 범위와 사용법

사용자가 선택한 범위는 설치·설정 창의 polkit 인증과 터미널의 `sudo` / `sudo -i` 인증이다. 각 인증에서 등록한 오른쪽 검지를 먼저 확인하고, 일치하면 비밀번호 없이 진행한다. 지문이 불일치하거나 약 10초 동안 손가락을 대지 않으면 기존 비밀번호 인증으로 넘어간다. 앱이 표시하는 안내 문구는 다를 수 있다.

PAM 방식에서는 지문과 비밀번호를 순서대로 확인한다. 지문을 확인하는 동안 비밀번호를 입력해도 지문 단계가 끝날 때까지 대기할 수 있다. 센서가 사용 중이거나 서비스를 사용할 수 없으면 비밀번호 인증으로 넘어간다.

## 설정 구성

- `/etc/pam.d/sudo`, `/etc/pam.d/sudo-i`: 기존 `common-auth` 앞에 `auth sufficient pam_fprintd.so max-tries=1 timeout=10`을 추가한다.
- `/etc/pam.d/polkit-1`: 같은 지문 인증을 먼저 시도하고, 나머지 인증·계정·암호 변경·세션 처리는 배포판의 `/usr/lib/pam.d/polkit-1`을 절대 경로로 포함한다.
- `/etc/pam.d/common-auth`와 비밀번호 인증은 그대로 유지한다. SSH 인증 설정을 변경하지 않는다.
- 원본 설정과 변경 전후 SHA-256은 `/var/lib/local-fingerprint-auth/2026-09-19/`에 root 전용으로 백업한다.

## 검증 결과

아직 적용되지 않았다. 설정 적용을 위한 기존 비밀번호 인증을 기다리던 중 2026-09-19 08:55:28에 GNOME 세션이 크래시했고, 이어서 polkit 인증이 실패했다. `/etc/pam.d/sudo`, `/etc/pam.d/sudo-i`는 원본이며 `/etc/pam.d/polkit-1`은 없다. 위 구성과 복구 스크립트는 준비된 계획이며 실제 인증 시험과 root 백업 생성도 아직 수행되지 않았다.

## 업데이트와 복구

`sudo`와 `sudo-i`는 패키지의 설정 파일이므로 패키지 업그레이드에서 설정 파일 처리 안내가 나올 수 있다. 배포판 설정으로 교체하면 여기서 추가한 지문 인증은 사라진다. polkit은 `/etc`의 로컬 설정을 사용하면서 `/usr/lib`의 배포판 설정을 포함하므로, 기존 경로가 유지되는 한 배포판의 후속 정책 변경도 반영한다. 큰 버전 업그레이드 후에는 두 종류의 인증을 다시 확인한다.

지문 센서의 별도 빌드 드라이버는 이 설정과 별도로 관리된다. 드라이버가 동작하지 않으면 비밀번호를 사용한다.

이 작업에서 추가한 관리자 지문 인증만 원복하려면:

```bash
python3 /home/testors/Documents/Codex/2026-09-19/f/outputs/restore-admin-fingerprint.py
```

또는 root 전용 백업에 보관한 복구 스크립트를 실행한다:

```bash
pkexec /usr/bin/python3 /var/lib/local-fingerprint-auth/2026-09-19/restore.py
```

복구 스크립트는 변경 이후 다른 편집이 없는지 확인한 뒤 sudo 설정을 복원하고 polkit의 로컬 설정을 제거한다. 이후 별도로 수정된 파일은 자동으로 덮어쓰지 않는다. 지문 등록 데이터와 센서 드라이버는 유지한다.

## 참고

- [Ubuntu pam_fprintd 매뉴얼](https://manpages.ubuntu.com/manpages/resolute/man8/pam_fprintd.8.html)
- [Linux-PAM 1.7.0 설정 파일 처리 소스](https://github.com/linux-pam/linux-pam/blob/v1.7.0/libpam/pam_handlers.c)
