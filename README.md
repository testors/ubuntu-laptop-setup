# Ubuntu 노트북 커스텀 패치 보관소

2026-09-19에 이 노트북에 적용한 변경의 **원본 소스, 패치, 검증된 바이너리, 재빌드·재설치·원복 도구**를 보관한다. 기존 Codex 작업 폴더나 특정 계정명 없이 이 디렉터리만 옮겨 사용할 수 있다.

| 구성 | 보관한 버전 / 목적 | 적용 범위 |
|---|---|---|
| `fingerprint` | libfprint 포크 `e105528`, EGIS `1c7a:05b1` 인식 | 해당 센서가 달린 기기의 fprintd 서비스 |
| `drag` | libinput `1.31.1-1ubuntu1.2` + shim `09e9ca7` | 사용자의 GNOME Wayland 세션; 빠른 세손가락 움직임도 드래그 처리 |
| `mutter` | `50.1-0ubuntu2.4+keymapfix1` | 키맵 변경 때 XKB 접근 경쟁 상태 수정 |
| 관리자 지문 인증 | **계획만 준비, 미적용** | [별도 상태 기록](pending/admin-fingerprint/README.md) |

보관 바이너리의 검증 환경은 **Ubuntu 26.04 amd64, GNOME 50**이다. 지문 드라이버는 USB ID가 일치해야 한다. 다른 Ubuntu 릴리스·CPU 아키텍처·GNOME 버전에서 그대로 설치하는 것을 차단한다. 같은 Ubuntu 안에서도 libinput 기준 버전이 다르거나 더 최신 Mutter가 설치되어 있으면 [업데이트 후 재적용 절차](docs/maintenance.md)를 따른다.

## 먼저 확인

```bash
cd ~/Repos/ubuntu
./ubuntu-custom verify
./ubuntu-custom status
```

`verify`는 소스·패치·바이너리·라이선스 31개 파일의 SHA-256을 확인한다. `status`는 장치, 설정 파일, 설치된 패키지 및 실행 중인 GNOME의 라이브러리를 조회한다. 재로그인이 필요한 경우 `RELOGIN REQUIRED`가 표시된다. 서비스·설정·패키지를 변경하지 않는다.

**보관 시점 상태:** 세 가지 변경 모두 설치되어 있다. Mutter는 현재 세션에서 아직 이전 라이브러리를 사용하므로 사용자가 작업을 저장한 뒤 재로그인해야 한다. 재로그인 후 실제 잠금·지문 해제 반복 시험은 남아 있다. 이번 정리 작업으로 시스템을 재설치하거나 세션을 재시작하지 않았다.

## 같은 환경에 설치하거나 설정이 사라졌을 때 복원

필요한 구성만 선택한다. 아래 명령은 **대상 데스크톱 사용자의 터미널에서, 전체 명령에 sudo를 붙이지 않고** 실행한다. 시스템 변경이 필요한 지문/Mutter 설치는 도구가 관리자 인증을 요청한다. 드래그는 사용자 설정이다.

```bash
# 실제 변경 없이 설치 가능 여부와 패키지 계획 확인
./ubuntu-custom install mutter --dry-run
./ubuntu-custom install fingerprint --dry-run
./ubuntu-custom install drag --dry-run

# 위 검사에 성공한 필요한 구성만 설치
./ubuntu-custom install mutter
./ubuntu-custom install fingerprint
./ubuntu-custom install drag
```

새 Ubuntu에는 `python3`, `fprintd`, `libpam-fprintd`가 필요하다. `sudo apt-get install python3 fprintd libpam-fprintd`로 설치할 수 있다. GNOME 데스크톱과 해당 장치 드라이버가 갖춰진 환경을 전제로 한다. 패키지 의존성 추가에는 인터넷/APT 저장소가 필요할 수 있다.

드래그·Mutter 설치 뒤 **작업을 저장하고 로그아웃 → 로그인**한다. 도구는 GNOME을 재시작하거나 자동 로그아웃하지 않는다. 새 기기의 지문은 이식하지 않고 다시 등록한다.

```bash
fprintd-enroll -f right-index-finger
fprintd-verify -f right-index-finger
```

드래그는 일반 Ubuntu의 `org.gnome.Shell@ubuntu.service`를 기본으로 사용한다. 다른 GNOME 세션은 실제 유닛 이름을 확인한 뒤 `--service org.gnome.Shell@wayland.service`처럼 지정한다. X11 및 타 데스크톱은 이 구성의 검증 범위 밖이다.

## 원복

```bash
# 먼저 같은 명령에 --dry-run을 붙여 확인할 수 있다.
./ubuntu-custom disable drag
./ubuntu-custom disable fingerprint
./ubuntu-custom rollback mutter
```

드래그·지문은 이 도구가 인식하는 서비스 설정만 제거하고 Ubuntu 기본 라이브러리를 다시 사용한다. 개인 지문 등록 데이터는 삭제하지 않는다. Mutter는 보관한 공식 `50.1-0ubuntu2.4` 패키지 4개로 돌아간다. 이미 다른 버전으로 업데이트되었다면 무작정 다운그레이드하지 않고 중단한다. 드래그·Mutter 원복도 재로그인 후 활성화된다. 로그인에 문제가 생겼을 때의 TTY 복구는 [유지보수 문서](docs/maintenance.md#로그인에-문제가-있을-때)에 있다.

## 소스에서 다시 빌드

[빌드 안내](docs/building.md)에 구성별 의존성과 최신 Ubuntu 소스로의 재적용 절차가 있다. 예:

```bash
./build-custom deps drag         # 설치할 의존성 명령을 출력만 한다.
./build-custom build drag        # build/drag 아래에만 소스·시험·결과 생성
./ubuntu-custom install drag --artifacts build/drag/artifacts --dry-run
./ubuntu-custom install drag --artifacts build/drag/artifacts
```

`build-custom`은 시스템 설치를 하지 않는다. 재빌드 산출물에는 실행 환경·기준 버전·파일 해시를 담은 새 `manifest.json`이 생성된다. 공식 업데이트에 수정이 이미 포함됐거나 패치가 충돌하면 강제 적용하지 않는다.

## 보관 구성과 범위

- `artifacts/`: 실제 사용 중이거나 설치 검증을 마친 바이너리, Mutter 공식 원복 패키지, 설치 명세.
- `sources/`, `patches/`, `licenses/`: 고정 커밋의 전체 소스, Ubuntu 원본 소스/패키징, 적용 패치, 원저작물 라이선스.
- `scripts/`, `tests/`: 이식 가능한 관리·빌드 도구, 실제 시스템을 건드리지 않는 보호 장치 시험.
- `docs/`: 빌드, 업데이트 대응, 일반 설정, 검증 범위. `docs/reports/`는 당시 보고서와 **과거 전용** 복구 스크립트.
- `pending/`: 아직 적용하지 않은 관리자 지문 인증 계획.

SSH 개인키, 실제 지문 템플릿, 비밀번호, 코어 덤프는 포함하지 않는다. 소스 프로젝트의 시험용 센서 자료는 원본 소스에 포함될 수 있으며 사용자의 등록 지문이 아니다. 이 디렉터리 전체를 백업하되 재생성 가능한 `build/`는 제외해도 된다. 외부 Git 저장소로 업로드하지 않았다.

[검증 결과](docs/validation.md) · [일반 설정과 공식 패키지](docs/settings.md) · [원본 출처](sources/provenance.json) · [라이선스 안내](licenses/README.md)
