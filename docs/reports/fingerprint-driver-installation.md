# 지문 센서 드라이버 설치 및 검증

날짜: 2026-09-19 (KST)

Fujitsu 노트북의 EGIS ETU906Axx-E 지문 센서(USB 1c7a:05b1)에 비공식 libfprint 드라이버를 빌드·적용했다. 센서 인식, 오른쪽 검지 등록, 등록한 손가락의 인증 성공, 다른 손가락의 인증 거부, 서비스 재시작 후 인증 성공을 실제로 확인했다.

## 설치 구성

- 원본: [likeablob/libfprint-fmv-etu906axx-e](https://github.com/likeablob/libfprint-fmv-etu906axx-e)
- 고정 커밋: e105528828a04dffde789cda48742c204183386d
- 기반 버전: libfprint 1.94.9, 드라이버 선택: egismoc
- Ubuntu 26.04에서 GCC 15, Meson 1.10.1로 빌드. 이 소스에 로컬 코드 패치를 추가하지 않았다.
- 설치 경로: /opt/fingerprint-egis-05b1/e105528/lib/libfprint-2.so.2.0.0
- SHA-256: 7787b1c874df1e97d469a9da0163818b76aa0175ec2e478ce27b5c9fd49edbf9
- 서비스 설정: /etc/systemd/system/fprintd.service.d/60-egis-05b1.conf
- fprintd 서비스에만 전용 라이브러리 경로를 지정했다. Ubuntu 패키지의 기본 libfprint 파일은 보존했다.
- 설치한 파일과 라이브러리 디렉터리는 root 소유이며 일반 사용자는 수정할 수 없다.

## 검증 결과

| 검사 | 결과 |
|---|---|
| 빌드 | 성공 |
| C 단위 테스트 | 장치·상태 관리 및 SDCP 시험 3개 통과, 이미지 조합 시험 1개 Cairo 의존성 부재로 건너뜀 |
| 기존 fprintd와 동적 연결 | 미해결 심볼 없음 |
| 센서 인식 | Egis Technology (LighTuning) Match-on-Chip 1개 |
| 오른쪽 검지 등록 | enroll-completed |
| 등록한 오른쪽 검지 인증 | verify-match |
| 등록하지 않은 왼쪽 검지 인증 | verify-no-match |
| 서비스 재시작 후 등록 목록 | 오른쪽 검지 유지 확인 |
| 서비스 재시작 후 오른쪽 검지 인증 | verify-match, 종료 코드 0 |

실제 장치 검사에서는 인증서·서명 검사와 등록 완료 오류 검사를 비활성화하지 않았다. 지문 템플릿이나 보안 통신 비밀값은 이 보고서에 수집하지 않았다.

첫 등록 시도는 손가락 감지 시간 초과로 실패했으며 취소 과정에서 서비스 경고가 기록됐다. 사용자가 준비된 뒤 다시 등록하자 정상 완료됐고, 일치/불일치 인증도 통과했다.

등록 과정에서 반환된 지문 객체의 저장 상태 표시 관련 드라이버 경고 1건이 기록됐다. 실제 등록 후 두 종류의 인증 결과는 정상적으로 구분됐다. 서비스 재시작 후 첫 인증은 손가락 감지 시간 초과였으며, 사용자가 아직 손가락을 대지 않았다고 확인했다. 바로 재시도하여 오른쪽 검지 인증 성공(verify-match, 종료 코드 0)을 확인했다. 이 드라이버의 손가락 감지 대기 시간은 약 10초이므로 인증이 시작되면 바로 센서에 손가락을 댄다.

GNOME 로그인 설정의 enable-fingerprint-authentication과 enable-password-authentication은 모두 true였다. 기존 gdm-fingerprint PAM 구성이 설치되어 있다. 비밀번호 로그인과 /etc/pam.d/common-auth를 변경하지 않았다. 로그인 화면 및 화면 잠금 해제 자체는 아직 직접 시험하지 않았다.

이 빌드에서는 GObject Introspection 기반 드라이버 모의 시험을 비활성화했다. 후속 덮개 닫기 시험에서 절전·복귀 후 센서 인식과 오른쪽 검지 등록 목록 유지를 확인했다. 절전 후 실제 손가락 인증과 전체 재부팅 후 동작은 아직 시험하지 않았다. 해당 프로젝트의 다른 센서에서는 [절전 후 서비스 문제](https://github.com/likeablob/libfprint-fmv-etu906axx-e/issues/2)가 보고되어 있다. [이 노트북의 절전 시험 결과](./lid-suspend-test-2026-09-19.md)

## 복구 방법

문제가 생기면 비밀번호로 로그인한 뒤 다음 명령으로 Ubuntu 기본 지문 드라이버로 복구한다.

```bash
pkexec /usr/bin/bash /opt/fingerprint-egis-05b1/e105528/rollback.sh
```

같은 복구 스크립트가 이 보고서와 함께 저장되어 있다: [rollback-fingerprint-driver.sh](./rollback-fingerprint-driver.sh).

복구는 이번에 만든 fprintd 서비스 설정만 제거하고 서비스를 다시 시작한다. 지문 등록 데이터와 비밀번호 인증은 삭제하거나 변경하지 않는다. 전용 드라이버 파일은 사용되지 않는 상태로 남는다.
