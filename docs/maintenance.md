# 업데이트 후 점검과 복구

자동 패키지 hold, 자동 재설치 hook, 자동 로그아웃은 구성하지 않는다. 보안 업데이트를 계속 받을 수 있도록 일반 APT 업데이트 흐름을 유지한다.

| 구성 | 업데이트 영향 | 대응 |
|---|---|---|
| 지문 | `/opt`의 사설 라이브러리와 `/etc` 서비스 설정은 보통 남지만 fprintd/의존 라이브러리 변화로 호환성이 달라질 수 있음 | `status`, 실제 지문 인증, 필요 시 재빌드/설정 재적용 |
| 드래그 | 사용자 설정은 남아도 새 libinput 대신 예전 사설 라이브러리가 계속 사용될 수 있음 | `REBUILD REQUIRED`가 나오면 현재 공식 libinput 소스 기준 재빌드 |
| Mutter | 더 높은 공식 패키지 버전이 로컬 패치를 교체할 수 있음 | 공식 수정 포함 여부 확인; 미포함이면 새 공식 소스에 재적용 |
| 관리자 지문 인증 | sudo 설정 파일을 배포판 원본으로 교체하면 지문 규칙이 없어질 수 있음 | `./admin-fingerprint status`, 필요 시 `install` 재적용 |

## 확인 순서

```bash
cd ~/Repos/ubuntu
./ubuntu-custom verify
./ubuntu-custom status
dpkg --audit
```

Mutter 관련 버전과 실행 중인 GNOME의 라이브러리 경로를 함께 본다. 설치 버전만 맞아도 세션이 이전 라이브러리를 계속 사용하면 패치가 활성화되지 않은 상태다. `RELOGIN REQUIRED`가 나오면 작업 저장 후 재로그인한다.

설정 파일만 사라졌고 OS/아키텍처/기준 패키지 버전이 그대로라면 해당 구성에 `install … --dry-run`, 이어서 `install …`을 실행한다. 기존의 초기 설치 경로도 인식하므로 이 저장소로 처음 복원할 때 별도로 기존 스크립트를 실행할 필요는 없다. 다른 프로그램이 편집한 알 수 없는 override는 자동 덮어쓰기를 거부한다.

libinput 또는 Mutter가 업데이트됐다면 [새 소스 빌드 절차](building.md#같은-ubuntu의-새-공식-소스로-재적용)를 사용한다. 공식 Mutter에 이미 수정이 포함되면 공식 패키지를 그대로 사용하며, 예전 `+keymapfix1` 문자열이 없어졌다는 이유만으로 되돌리지 않는다.

## 관리 경로

| 구성 | 새 관리 도구로 설치하는 경로 |
|---|---|
| 지문 라이브러리 | `/opt/ubuntu-custom/fingerprint/<해시>/lib/` |
| 지문 서비스 설정 | `/etc/systemd/system/fprintd.service.d/60-egis-05b1.conf` |
| 드래그 라이브러리 | `$HOME/.local/lib/ubuntu-custom/drag/<해시>/` |
| 드래그 설정 | `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/org.gnome.Shell@ubuntu.service.d/60-three-finger-drag.conf` |
| 드래그 설치 기록 | `${XDG_STATE_HOME:-$HOME/.local/state}/ubuntu-custom/drag/` |
| 시스템 설치 기록/원복 패키지 | `/var/lib/ubuntu-custom/` |
| 관리자 지문 인증 백업/원복 도구 | `/var/lib/ubuntu-custom/admin-fingerprint/<백업ID>/` |

원래 설치는 지문 `/opt/fingerprint-egis-05b1/e105528/`, 드래그 `$HOME/.local/lib/enable-3fg-drag/`, Mutter 복구 `/var/lib/local-mutter-keymap-fix/`를 사용했다. 이번 보관 작업은 현재 경로를 바꾸지 않았다. 이후 새 도구로 설치하면 위 새 경로를 사용한다. 라이브러리는 실행 중 파일을 잘라 쓰지 않고 새 파일로 교체한다.

지문 설치는 동적 연결 검사 후 fprintd를 재시작하고 센서가 노출되는지 확인한다. 이 단계가 실패하면 직전 설정으로 돌아간다. 드래그는 동적 연결 검사 후 사용자 systemd 설정만 reload한다. 지문/드래그의 비활성화는 OS 버전이 바뀌어도 가능하다.

Mutter 설치는 먼저 APT 계획을 확인하고 패키지 삭제가 필요한 작업을 거부한다. 원복 패키지를 root 전용 위치에 확보한 뒤 설치한다. APT 자체가 중간에 실패하면 `dpkg --audit` 결과를 확인하고 오류 메시지에 나온 보관 디렉터리를 사용해 복구한다. 필요하면 `./ubuntu-custom rollback mutter --artifacts /var/lib/ubuntu-custom/mutter/<해시> --dry-run`으로 원복 계획을 확인한다. 정상 재설치·원복은 모두 APT를 통해 처리한다.

## 로그인에 문제가 있을 때

Ctrl+Alt+F3으로 TTY에 전환해 해당 사용자로 로그인한다. 경로는 보관소를 옮긴 위치로 바꾼다.

```bash
cd ~/Repos/ubuntu
./ubuntu-custom disable drag
./ubuntu-custom disable fingerprint
./ubuntu-custom rollback mutter --dry-run
# 설치 버전이 보관된 패치/공식 버전에 해당할 때만:
./ubuntu-custom rollback mutter
```

텍스트 콘솔에서는 관리자 작업에 sudo를 사용한다. 드래그는 sudo 없이 실행해야 실제 사용자 설정을 찾는다. `systemctl --user`에 연결할 수 없는 복구 환경이면 위 표의 해당 드래그 override를 `.disabled` 확장자로 옮긴 뒤 다음 로그인으로 복구할 수 있다. 다른 override가 있으면 내용을 먼저 확인한다. 더 최신 Mutter가 설치된 경우에는 이 보관본을 강제 다운그레이드하지 말고 현재 배포판 공식 패키지로 복구한다.

지문 등록은 기기별로 다시 수행하며 센서 초기화나 기존 등록 삭제를 자동화하지 않는다. `ubuntu-custom`의 드라이버 설치는 PAM을 변경하지 않는다. 별도 `admin-fingerprint` 도구가 sudo/polkit의 PAM 설정을 관리한다. [자세한 적용·복구 절차](admin-fingerprint.md)를 참고한다.
