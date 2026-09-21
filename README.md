# Ubuntu Laptop Setup

2026-09-19에 이 노트북에 적용한 변경의 **원본 소스, 패치, 검증된 바이너리, 재빌드·재설치·원복 도구**를 보관한다. 기존 Codex 작업 폴더나 특정 계정명 없이 이 디렉터리만 옮겨 사용할 수 있다.

| 구성 | 보관한 버전 / 목적 | 적용 범위 |
|---|---|---|
| `fingerprint` | libfprint 포크 `e105528`, EGIS `1c7a:05b1` 인식 | 해당 센서가 달린 기기의 fprintd 서비스 |
| `drag` | libinput `1.31.1-1ubuntu1` / `1.31.1-1ubuntu1.2` + shim `09e9ca7` | 사용자의 GNOME Wayland 세션; 빠른 세손가락 움직임도 드래그 처리 |
| `mutter` | `50.1-0ubuntu2.4+keymapfix1` | 키맵 변경 때 XKB 접근 경쟁 상태 수정 |
| 관리자 지문 인증 | 지문 우선, 약 10초 뒤 비밀번호 fallback | **적용 완료**: sudo/sudo-i 및 설치·설정 창; [안내](docs/admin-fingerprint.md) |
| 잠금화면 바로 인증 | GNOME 50용 `Direct Unlock Prompt` 확장 | 화면 복귀 시 현재 계정 인증창 자동 표시; [설치·원복](docs/direct-unlock.md) |

보관 바이너리의 검증 환경은 **Ubuntu 26.04 amd64, GNOME 50**이다. 지문 드라이버는 USB ID가 일치해야 한다. 다른 Ubuntu 릴리스·CPU 아키텍처·GNOME 버전에서 그대로 설치하는 것을 차단한다. 같은 Ubuntu 안에서도 libinput 기준 버전이 다르거나 더 최신 Mutter가 설치되어 있으면 [업데이트 후 재적용 절차](docs/maintenance.md)를 따른다.

## 먼저 확인

```bash
cd ~/Repos/ubuntu-laptop-setup
./ubuntu-custom verify
./ubuntu-custom status
```

`verify`는 소스·패치·바이너리·라이선스의 SHA-256을 확인한다. `status`는 장치, 설정 파일, 접근 가능한 설치 기록(`state.json`), 패키지 버전, 실행 중인 GNOME 라이브러리를 조회한다. 재로그인이 필요한 경우 `RELOGIN REQUIRED`가 표시된다. 서비스·설정·패키지를 변경하지 않는다.

`install drag`는 현재 `libinput10`과 기준 버전이 같은 보관본을 고른다. `install mutter`는 같은 기준 버전이나 유일한 안전한 업그레이드 보관본을 고른다. 보관본(`artifacts/*/by-base/<버전>/` 또는 기본 디렉터리)이 맞지 않으면 공식 소스를 받아 패치를 적용·빌드한 뒤 설치한다(빌드 의존성 필요). 자동 재빌드를 막으려면 `--no-rebuild`를 붙인다. 보관본이 없는 버전의 `--dry-run`은 재빌드 계획만 보여 주며, 소스 확보와 패치 적용 가능 여부는 실제 빌드에서 확인한다.

**현재 상태(2026-09-19 후속 확인):** 세 가지 드라이버/세션 변경과 관리자 지문 인증이 적용되어 있다. 새 GNOME 세션에서 설치된 Mutter 키맵 패치 라이브러리를 사용하는 것을 확인했다. 잠금화면 바로 인증 확장도 설치되어 `ACTIVE` 상태다. 실제 Enter 없는 잠금·지문 해제와 반복 시험은 남아 있다. 설치 도구가 세션을 강제로 재시작하지는 않는다.

## 같은 환경에 설치하거나 설정이 사라졌을 때 복원

필요한 구성만 선택한다. 아래 명령은 **대상 데스크톱 사용자의 터미널에서, 전체 명령에 sudo를 붙이지 않고** 실행한다. 시스템 변경이 필요한 지문/Mutter 설치는 도구가 관리자 인증을 요청한다. 드래그는 사용자 설정이다.

```bash
# 실제 변경 없이 설치 가능 여부와 패키지 계획 확인
./ubuntu-custom install mutter --dry-run
./ubuntu-custom install fingerprint --dry-run
./ubuntu-custom install drag --dry-run

# 위 검사에 성공한 필요한 구성만 설치 (버전 불일치 시 drag/mutter는 자동 재빌드 가능)
./ubuntu-custom install mutter
./ubuntu-custom install fingerprint
./ubuntu-custom install drag

# 보관본만 쓰고 자동 재빌드를 거부
./ubuntu-custom install drag --no-rebuild --dry-run
```

새 Ubuntu에는 `python3`, `fprintd`, `libpam-fprintd`가 필요하다. `sudo apt-get install python3 fprintd libpam-fprintd`로 설치할 수 있다. GNOME 데스크톱과 해당 장치 드라이버가 갖춰진 환경을 전제로 한다. 패키지 의존성 추가에는 인터넷/APT 저장소가 필요할 수 있다.

드래그·Mutter 설치 뒤 **작업을 저장하고 로그아웃 → 로그인**한다. 도구는 GNOME을 재시작하거나 자동 로그아웃하지 않는다. 새 기기의 지문은 이식하지 않고 다시 등록한다.

```bash
fprintd-enroll -f right-index-finger
fprintd-verify -f right-index-finger
```

관리자 작업에서도 지문을 사용하려면, 등록 후 다음을 적용한다. [관리자 지문 인증 안내](docs/admin-fingerprint.md)에 상세 설정과 원복 절차가 있다.

```bash
./admin-fingerprint install --dry-run
./admin-fingerprint install
```

잠금화면에서 Enter 없이 지문 인증창을 표시하려면 다음 확장을 설치하고 재로그인한다. [확장 안내](docs/direct-unlock.md)에 동작 범위와 검증 방법이 있다.

```bash
./direct-unlock install --dry-run
./direct-unlock install
./direct-unlock status
```

드래그는 일반 Ubuntu의 `org.gnome.Shell@ubuntu.service`를 기본으로 사용한다. 다른 GNOME 세션은 실제 유닛 이름을 확인한 뒤 `--service org.gnome.Shell@wayland.service`처럼 지정한다. X11 및 타 데스크톱은 이 구성의 검증 범위 밖이다.

## 원복

```bash
# 먼저 같은 명령에 --dry-run을 붙여 확인할 수 있다.
./ubuntu-custom disable drag
./ubuntu-custom disable fingerprint
./ubuntu-custom rollback mutter
./admin-fingerprint rollback
./direct-unlock disable
```

드래그·지문은 이 도구가 인식하는 서비스 설정만 제거하고 Ubuntu 기본 라이브러리를 다시 사용한다. 개인 지문 등록 데이터는 삭제하지 않는다. Mutter는 설치할 때 함께 저장한 같은 기준 버전의 공식 패키지 4개로 돌아간다. 설치 기록이 없으면 보관한 `50.1-0ubuntu2.4` 패키지를 사용한다. 이미 다른 버전으로 업데이트되었다면 무작정 다운그레이드하지 않고 중단한다. 드래그·Mutter 원복도 재로그인 후 활성화된다. 로그인에 문제가 생겼을 때의 TTY 복구는 [유지보수 문서](docs/maintenance.md#로그인에-문제가-있을-때)에 있다.

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

- `artifacts/`: 검증된 바이너리와 Mutter 원복 패키지. drag/mutter는 `by-base/<기준버전>/`에 추가 버전을 둘 수 있다.
- `sources/`, `patches/`, `licenses/`: 고정 커밋의 전체 소스, Ubuntu 원본 소스/패키징, 적용 패치, 원저작물 라이선스.
- `scripts/`, `tests/`: 이식 가능한 관리·빌드 도구, 실제 시스템을 건드리지 않는 보호 장치 시험.
- `extensions/`: GNOME 50용 잠금화면 확장 소스와 라이선스.
- `docs/`: 빌드, 업데이트 대응, 일반 설정, 검증 범위. `docs/reports/`는 당시 보고서와 **과거 전용** 복구 스크립트.
- `pending/`: 최초 보관 당시 미적용이었던 계획의 후속 상태 링크. 관리자 지문 인증은 이후 적용 완료.

SSH 개인키, 실제 지문 템플릿, 비밀번호, 코어 덤프는 포함하지 않는다. 소스 프로젝트의 시험용 센서 자료는 원본 소스에 포함될 수 있으며 사용자의 등록 지문이 아니다. 이 디렉터리 전체를 백업하되 재생성 가능한 `build/`는 제외해도 된다. GitHub의 [testors/ubuntu-laptop-setup](https://github.com/testors/ubuntu-laptop-setup)에 보관한다.

[검증 결과](docs/validation.md) · [일반 설정과 공식 패키지](docs/settings.md) · [원본 출처](sources/provenance.json) · [라이선스 안내](licenses/README.md)
