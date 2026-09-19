# 세 손가락 드래그 설정

2026-09-19, Ubuntu 26.04.1 / GNOME Shell 50.1 / Wayland / libinput 1.31.1

**빠른 세 손가락 움직임도 드래그로 처리하도록 수정한 드라이버를 설치했다. 작업을 저장하고 로그아웃한 뒤 다시 로그인해야 새 버전이 적용된다.** 화면 잠금 해제만으로는 적용되지 않는다.

## 현재 설정과 사용 방법

- 세 손가락으로 움직이면 드래그한다. 이전 버전의 빠른 움직임 판별을 거치지 않으므로 드래그를 위해 일부러 잠깐 멈출 필요가 없다.
- 세 손가락 드래그가 켜진 경우, 해당 움직임의 스와이프 시작·이동·종료 이벤트를 만들지 않아 데스크톱 전환과 충돌하지 않도록 했다.
- 네 손가락 스와이프와 키보드 단축키의 데스크톱 전환은 유지한다.
- 기존 한 손가락 탭, 두 손가락 스크롤 설정은 유지했다. 세 손가락 탭과 드래그를 구분하는 기존 동작은 남아 있다.

처음 설치한 보완 모듈은 libinput의 기본 기능을 켜는 역할이어서 빠른 스와이프도 허용했다. 이번에는 Ubuntu의 현재 libinput 소스에 작은 변경을 추가해 세 손가락 드래그가 속도에 따라 스와이프로 바뀌지 않게 했다. [원본 보완 모듈 설명](https://github.com/joaodriessen/enable-3fg-drag)

## 검증 결과

| 검사 | 결과 |
|---|---|
| 기존 보완 모듈의 실제 로그인 적용 | 03:55:08 GNOME 로그에서 실제 06CB:CED3 터치패드 활성화 Success 확인 |
| 수정한 libinput 빌드 | 성공 |
| 빠른 동작 통합 시험 | 40개 통과, 하드웨어 조건이 맞지 않는 40개는 해당 없음, 실패 0 |
| 통합 시험 내용 | 탭 활성/비활성 상태에서 빠른 세 손가락 움직임이 왼쪽 버튼 누름 → 포인터 이동 → 버튼 해제로 이어지고 스와이프 이벤트가 없음을 검사; 네 손가락 스와이프 유지도 검사 |
| 비관리자 시험 | 10개 시험 그룹 통과. 최초에는 pytest 부재로 1개 실패했으나 작업 폴더에 의존성을 준비한 뒤 해당 검사를 재실행해 통과 |
| 기본 libinput의 공개 심볼 호환성 | 누락된 심볼 없음 |
| GNOME 동적 연결 | 전용 libinput 로딩 및 미해결 심볼 없음 |
| 설치본을 불러온 GNOME 버전 조회 | 정상 종료 |
| 현재 GNOME 세션 | PID 50634 유지. 새 libinput은 아직 로딩되지 않아 재로그인 필요 |

전체 libinput 하드웨어 시험을 실행한 것은 아니다. 수정한 버전의 실제 터치패드 사용감과 새 로그인 후 드래그는 아직 직접 확인하지 않았다. 가상 장치 시험이 만든 임시 udev 규칙은 시험 종료 뒤 제거됐다.

## 설치 내역

기존 활성화 모듈:

- 원본: https://github.com/joaodriessen/enable-3fg-drag
- 커밋: `09e9ca763eca05c33a183c7a6cf582bdd77dbbb1`
- 라이브러리: `/home/testors/.local/lib/enable-3fg-drag/09e9ca7/libenable-3fg-drag.so`

수정한 입력 드라이버:

- [Ubuntu 원본 소스 명세](https://archive.ubuntu.com/ubuntu/pool/main/libi/libinput/libinput_1.31.1-1ubuntu1.2.dsc): `libinput 1.31.1-1ubuntu1.2`, Ubuntu 패치 포함.
- [로컬 변경 패치](./three-finger-drag-native.patch): 드래그 판별 변경과 그에 맞춘 빠른 동작 시험.
- 디렉터리: `/home/testors/.local/lib/enable-3fg-drag/libinput-1.31.1-drag-only-v1`
- 라이브러리 SHA-256: `46626c233a6d657c007792c70dae2ab723aa5ae1305e023527146437a877d94f`
- libwacom·mtdev 지원을 유지했다. 라이브러리의 빌드 폴더 참조 경로는 설치 단계에서 제거했다.
- 이 전용 빌드는 APT가 자동 갱신하지 않는다. 향후 libinput 업데이트를 반영하려면 전용 빌드를 갱신하거나 아래 해제 명령으로 시스템 버전으로 돌아가야 한다.

서비스 설정은 `/home/testors/.config/systemd/user/org.gnome.Shell@ubuntu.service.d/60-three-finger-drag.conf`에 저장했다. testors 사용자의 Ubuntu GNOME 서비스에 LD_PRELOAD와 LD_LIBRARY_PATH를 지정했으며, 서비스가 직접 실행한 자식 프로세스에는 환경이 상속될 수 있다. 시스템 libinput 패키지와 `/etc/ld.so.preload`는 변경하지 않았다.

## 원래 설정으로 복구

testors 계정에서 다음 명령을 실행하고 로그아웃·로그인한다. 관리자 권한은 필요하지 않다.

```bash
bash /home/testors/.local/lib/enable-3fg-drag/libinput-1.31.1-drag-only-v1/disable.sh
```

추가한 GNOME 서비스 설정만 제거하며, 현재 세션을 종료하지 않는다. 라이브러리 파일은 남겨 둔다. 동일한 스크립트: [disable-three-finger-drag.sh](./disable-three-finger-drag.sh).

## 작업 중 보고된 갑작스러운 로그아웃

03:48:21 KST에 당시 GNOME Shell PID 8621이 SIGSEGV(신호 11)로 충돌했고, 사용자 세션이 종료된 기록을 확인했다. 이 시점에는 GNOME에 모듈을 적용하는 설정이 없었고 충돌 보고서의 메모리 매핑에도 모듈이 없었다. 별도 장치 검사 프로세스에서는 03:48:14에 모듈을 사용했다. 로그아웃 명령이나 GNOME 재시작 명령을 실행하지 않았다. 시간상 가까운 사건이지만 충돌의 구체적인 원인이나 검사와의 인과관계는 현재 자료만으로 확정하지 않았다.
