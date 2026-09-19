# 관리자 지문 인증: 미적용

설치·설정 창(polkit)과 터미널 sudo/sudo-i에서 지문을 먼저 확인하고 약 10초 뒤 비밀번호로 넘어가는 구성을 계획했다. 그러나 적용을 위한 인증 도중 GNOME이 크래시했으므로 실제 변경은 완료되지 않았다.

2026-09-19 확인 당시 `/etc/pam.d/sudo`와 `sudo-i`는 원본이고, `/etc/pam.d/polkit-1`은 없다. 공통 PAM 설정도 이 작업에서 변경하지 않았다. root 전용 백업과 실제 관리자 지문 인증 시험 역시 완료되지 않았다.

따라서 이 항목은 재설치 목록에서 제외한다. `ubuntu-custom install fingerprint`는 센서 드라이버만 설치하며 관리자 PAM 인증을 활성화하지 않는다. 향후 별도 적용할 때에는 해당 Ubuntu의 PAM 원본을 다시 확인하고 백업, 비밀번호 fallback, sudo/polkit 인증, 화면 잠금 해제를 함께 시험해야 한다.

당시 계획은 [원본 보고서](../../docs/reports/admin-fingerprint-authentication.md)에 보존했다. 그 문서의 고정 경로와 복구 스크립트는 당시 환경용이며 현재 설치 절차로 실행하지 않는다.
