# 잠금화면에서 바로 지문 인증

`Direct Unlock Prompt`는 GNOME 50의 잠금화면이 깨어날 때 현재 사용자의 기본 인증창을 자동으로 연다. 시계 화면에서 Enter를 누르거나 클릭하는 한 단계를 생략한다. 지문이 등록되어 있고 GNOME의 지문 인증이 켜져 있으면 기존 인증창이 지문을 기다린다. 비밀번호도 그대로 사용할 수 있다.

## 설치와 확인

GNOME 데스크톱 사용자의 터미널에서 실행한다. sudo는 사용하지 않는다. Ubuntu의 `python3-gi`, `gnome-shell`이 필요하다.

```bash
cd ~/Repos/ubuntu-laptop-setup
./direct-unlock install --dry-run
./direct-unlock install
./direct-unlock status
```

기본 설치 위치는 `~/.local/share/gnome-shell/extensions/direct-unlock@testors.github.io/`다. `XDG_DATA_HOME`이 지정되어 있으면 해당 경로를 사용한다. 다른 확장의 활성화 설정은 유지한다. 모든 사용자 확장이 전역으로 꺼져 있거나 시스템 정책이 설치를 막으면 중단한다.

**처음 설치하거나 코드가 바뀌면 작업을 저장하고 로그아웃 → 로그인해야 한다.** 현재 Shell은 새 확장 디렉터리를 자동 검색하지 않으며, 불러온 JavaScript 모듈도 캐시한다. 도구는 확장을 다음 로그인에 활성화하도록 등록하고 `RELOGIN REQUIRED`를 출력한다. 세션을 강제 종료하지 않는다. 상태 조회에서 `Running Shell: ACTIVE`가 나와야 실행 중이다. 파일 설치와 설정 등록만 된 상태를 실제 실행 중으로 취급하지 않는다.

2026-09-19 후속 확인에서 이 노트북의 새 GNOME 세션에 확장이 `ACTIVE` 상태이며, 이전에 설치한 Mutter 키맵 패치 라이브러리도 로드된 것을 확인했다. 최초 설치 안내와 달리 현재 이 노트북은 추가 재로그인이 필요하지 않다. 실제 지문 해제 시험은 별도로 남아 있다.

## 동작과 범위

- 사용자 세션의 잠금 해제에 적용한다. 부팅 직후의 GDM 사용자 선택 화면은 변경하지 않는다.
- GNOME의 기존 `UnlockDialog.activate()`로 현재 계정의 인증창을 연다. PAM 정책, 지문 드라이버, 인증 결과, 잠금 해제 판단은 변경하지 않는다.
- 화면이 가려져 있거나 절전 중이면 인증을 시작하지 않는다. 잠금·화면 복귀·화면 가림 해제 이벤트를 모아 다음 idle callback에서 상태를 다시 확인한다.
- 이미 인증창이 표시되어 있으면 비밀번호 입력과 진행 중인 인증을 유지한다. 실패·취소 이벤트에 자동 재시도를 걸지 않는다. Esc, 인증 시간 제한과 시도 횟수는 GNOME/GDM의 원래 동작을 따른다.
- 지문 센서 터치만으로 꺼진 화면이나 절전 상태에서 깨우는 기능은 추가하지 않는다. 먼저 덮개 열기·키보드·터치패드 등으로 화면을 깨워야 할 수 있다.
- 기존 비공식 지문 드라이버의 시간 초과 후 응답 오류를 수정하는 확장은 아니다. 해당 문제와 비밀번호 fallback은 [관리자 지문 인증 문서](admin-fingerprint.md)에 기록되어 있다.

`user`와 `unlock-dialog` 세션 모드에서만 동작하며 메서드를 덮어쓰지 않는다. 비활성화 시 등록한 신호와 대기 중인 idle callback을 모두 해제한다. GNOME 내부 API를 사용하므로 지원 버전은 50으로 제한했다. GNOME 주요 버전이 바뀌면 새 소스로 검증하기 전에 `shell-version` 숫자만 늘려 강제 활성화하지 않는다.

## 원복과 업데이트

```bash
./direct-unlock disable
```

이 확장만 비활성화하고 설치 파일은 보관한다. 실행 중인 GNOME은 설정 변경에 따라 확장을 비활성화한다. 다음 잠금에서 원래 시계 화면으로 돌아간다. 설정이 갱신되지 않는 환경에서는 재로그인한다. GUI의 확장 관리 앱에서 `Direct Unlock Prompt`를 꺼도 된다. 그래픽 로그인에 문제가 생기면 같은 사용자의 TTY에서 아래 명령으로 다음 로그인 때 확장을 끌 수 있다.

```bash
dbus-run-session -- ./direct-unlock disable
```

재적용은 `./direct-unlock install`이다. 설치 파일이 변경되거나 출처를 확인할 수 없으면 덮어쓰지 않고 중단한다. 소스 수정 후 배포 시 `metadata.json`의 `version`을 올린다. 업그레이드 이전 파일은 `~/.local/state/ubuntu-custom/direct-unlock/backup-*/`에 보관한다(`XDG_STATE_HOME` 지원). GNOME 설정 저장에 실패하면 이전 설정과 설치 파일을 복원한다.

## 검증

```bash
gjs -m tests/test_direct_unlock.js
/usr/bin/python3 -m unittest discover -s tests -p 'test_*.py'
```

GJS 시험은 실제 controller 코드와 Shell 의존성만 대체한 extension adapter를 실행한다. 잠금/화면 복귀, 중복 이벤트, 입력 중 보호, 절전/복귀, 실패·취소 후 재시도 없음, 비활성화 시 신호·callback 정리를 확인한다. Python 시험은 임시 디렉터리와 모의 설정에서 설치/재설치/원복, 변경 파일 보존, 정책 저장 실패 복원과 업그레이드 백업을 확인한다. 실제 잠금 해제나 지문 성공을 대신하는 시험은 아니다.

재로그인 후 사용자가 확인할 항목:

1. `./direct-unlock status`에 `ACTIVE`가 표시되는지 확인한다.
2. 잠근 뒤 화면을 깨워 Enter 없이 현재 계정의 인증창이 보이는지 확인한다.
3. 등록한 손가락으로 해제하고, 다시 잠근 뒤 비밀번호로도 해제한다.
4. 덮개를 닫았다 열어 복귀할 때 확인한다. 실패·취소·시간 초과 시 비밀번호 경로가 유지되는지 확인한다.

참고: [GNOME 확장의 잠금화면 세션 모드](https://gjs.guide/extensions/topics/session-modes.html), [Shell 재시작과 디버깅](https://gjs.guide/extensions/development/debugging.html). 구현은 이 노트북의 Ubuntu GNOME Shell 50.1 리소스(`unlockDialog.js`, `screenShield.js`, `lightbox.js`)를 확인해 작성했다. 확장 자체의 라이선스는 소스 디렉터리의 MIT LICENSE다.
