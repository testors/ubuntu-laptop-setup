# 코드 패치 외의 설정과 공식 패키지

이 문서는 2026-09-19에 확인한 상태와 작업 범위를 기록한다. 장치별 설정을 다른 기기에 일괄 적용하지 않는다.

## 한글 입력과 터치패드

보관 시점의 입력 소스는 `[('xkb', 'kr+kr104'), ('ibus', 'hangul')]`, 입력 소스 전환은 `['<Super>space', 'XF86Keyboard']`, 터치패드 tap-to-click은 `true`다. 한글 입력기는 `ibus-hangul`을 사용한다. 새 기기에서 같은 개인 설정을 원할 때 해당 사용자의 GNOME 터미널에서 다음을 실행할 수 있다.

```bash
sudo apt-get install ibus-hangul
gsettings set org.gnome.desktop.input-sources sources "[('xkb', 'kr+kr104'), ('ibus', 'hangul')]"
gsettings set org.gnome.desktop.wm.keybindings switch-input-source "['<Super>space', 'XF86Keyboard']"
gsettings set org.gnome.desktop.peripherals.touchpad tap-to-click true
```

입력 소스 목록은 위 값으로 교체된다. 다른 언어를 함께 쓰거나 키보드 배열이 다르면 GNOME 설정에서 직접 맞춘다. 드래그 패치는 이 키보드 설정을 변경하지 않는다.

## 영상 가속과 시스템 업데이트

공식 Ubuntu `intel-media-va-driver`와 `libigdgmm12`를 설치했다. Intel iHD 초기화와 코덱 프로파일 조회를 확인했다. 커스텀 GPU 패치, 커널 모듈 교체, DKMS 모듈은 만들지 않았다. 같은 Intel 계열 기기는 `sudo apt-get install intel-media-va-driver`로 공식 패키지를 설치한다. 다른 GPU에는 해당 GPU의 공식 드라이버를 선택한다.

당시 일반 APT 업데이트도 수행했지만 과거 전체 패키지 버전으로 시스템을 되돌리는 스크립트는 포함하지 않는다. 새 설치/업데이트에서는 배포판의 현재 업데이트를 받는다. 자세한 당시 목록은 [노트북 점검 보고서](reports/ubuntu-laptop-audit-2026-09-19.md)에 있다.

## 전원 관리

별도 전원 관리 패치는 설치하지 않았다. 기본 power-profiles-daemon/thermald/logind와 s2idle을 사용한다. AC 연결 상태에서 덮개 닫기 → 약 74초 절전 → 복귀, 하드웨어 저전력 상태 약 72.7초, 실패 0회를 확인했다. 다른 기기에 이 수치를 보장하지 않으며 배터리 장시간 측정은 수행하지 않았다. [시험 보고서](reports/lid-suspend-test-2026-09-19.md)를 참고한다.

## SSH

Windows에서 옮긴 SSH 개인키와 ssh-agent 문제는 인증 자격 증명 및 에이전트 상태에 관한 별도 항목이다. 이 보관소에는 `.ssh` 파일이나 에이전트 키를 넣지 않았다. 다른 시스템에는 키를 별도 보안 경로로 옮기고 소유권·권한과 `ssh-add -l` 결과를 확인한다. 이 패치 도구가 SSH나 서버 인증 설정을 변경하지 않는다.
