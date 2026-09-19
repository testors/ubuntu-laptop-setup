# 빌드와 소스 교체

검증 대상은 Ubuntu 26.04이며 기본 빌드 병렬도는 CPU 수와 8 중 작은 값이다. `--jobs 4`로 줄일 수 있다. 빌드는 일반 사용자로 한다. root 실행은 거부한다. 기존 작업 폴더 없이 `sources/`의 보관본에서 시작한다.

## 준비 및 의존성

```bash
./build-custom deps fingerprint
./build-custom deps drag
./build-custom deps mutter       # 먼저 기본 빌드 도구 설치 명령 확인
# 출력된 기본 빌드 도구 설치 명령 실행 후:
./build-custom prepare mutter
./build-custom deps mutter
```

`deps`는 필요한 APT 명령을 **출력만** 한다. 출력된 명령을 실행해 의존성을 설치한 뒤 빌드한다. Mutter는 먼저 원본 패키징을 풀어야 `apt-get build-dep /절대경로/source`를 사용할 수 있다. `deb-src` 설정 없이도 준비한 로컬 소스의 build-dep를 이용할 수 있다. 다른 릴리스에서는 패키지 이름·ABI·시험 요구사항 검토가 필요하므로 현재 도구가 중단한다.

보관 소스는 SHA-256 검사 후 추출하며, Ubuntu 소스는 `dpkg-source`로 Ubuntu 패치를 먼저 적용한다. `dpkg-source`가 업로더 공개키를 시스템 키링에서 못 찾았다는 경고를 표시할 수 있다. Mutter의 최초 취득 당시 서명 검증용 공개키는 `sources/mutter/uploader-key.asc`에 있다. 저장소 SHA-256 검사는 보관 이후 변조 여부의 확인이며 새로운 외부 소스의 진위를 보증하지 않는다.

## 지문 드라이버

```bash
./build-custom build fingerprint
./ubuntu-custom install fingerprint --artifacts build/fingerprint/artifacts --dry-run
./ubuntu-custom install fingerprint --artifacts build/fingerprint/artifacts
```

egismoc만 활성화하고 introspection, hwdb 설치, udev 규칙 설치, 문서·GTK 예제를 비활성화한다. 4개 라이브러리 단위 시험 그룹을 실행한다. 호스트 전체의 libfprint를 교체하지 않고 fprintd 서비스에만 적용한다.

이 포크의 데이터 생성/메타데이터 시험은 위 라이브러리 시험과 별개다. 전체 시험 실행 시 기존 USB ID 중복 관련 hwdb 경고와 온라인 AppStream URL 검사 실패가 관찰되었다. 실제 사용하지 않는 hwdb/AppStream 생성 검사를 빌드 성공 조건에 넣지 않았다. 실제 지문 등록·일치/불일치·절전 후 인증은 대상 하드웨어에서 별도로 확인한다.

## 드래그

```bash
./build-custom build drag
./ubuntu-custom install drag --artifacts build/drag/artifacts --dry-run
./ubuntu-custom install drag --artifacts build/drag/artifacts
```

Ubuntu libinput 소스에 `patches/drag-only.patch`를 적용한다. libinput의 native 세손가락 드래그를 shim으로 활성화하고, 빠른 움직임이 swipe로 전환되는 분기를 수정한다. 세손가락 swipe가 GNOME으로 전달되지 않아 데스크톱 전환으로 잘못 처리되지 않는다. 네손가락 처리와 다른 제스처는 원본 동작을 유지한다.

일반 사용자로 실행 가능한 9개 시험 그룹과, `check` 의존성이 있으면 litest 자체 시험 1개를 실행한다. 의존성을 뒤늦게 설치한 경우 `meson setup --reconfigure build/drag/meson-build` 후 다시 빌드한다. uinput을 사용하는 전체 하드웨어 시험은 자동으로 실행하지 않는다. 최초 설치에서 빠른 세손가락 드래그 관련 시험 40개 통과, 해당하지 않는 장치 조합 40개를 확인했다. 실제 터치패드의 선택·창 이동·빠른 드래그·버튼 해제를 재로그인 후 확인한다.

사설 libinput의 기준 버전이 설치된 `libinput10`과 정확히 일치해야 설치할 수 있다. 업데이트 뒤 더 오래된 사설 라이브러리가 계속 선택되는 것을 알아차릴 수 있도록 `status`에서도 버전 차이를 표시한다.

## Mutter

```bash
./build-custom deps mutter
# 출력된 기본 빌드 도구 설치 명령 실행
./build-custom prepare mutter
./build-custom deps mutter
# 출력된 빌드 의존성 설치 명령 실행
./build-custom build mutter
./ubuntu-custom install mutter --artifacts build/mutter/artifacts --dry-run
./ubuntu-custom install mutter --artifacts build/mutter/artifacts
```

Ubuntu 패치 시리즈에 GNOME 커밋 `709ef34381e51e83327b9c6d7270ed437d714768`을 추가하고 Debian changelog 버전을 `기준버전+keymapfix1`로 만든다. 원래의 Debian 패키징·시험을 사용한다. 상속된 `GDK_BACKEND`, 화면·세션 버스 환경값, `nocheck` 옵션을 제거하고 별도 runtime 디렉터리를 사용한다. 빌드와 시험에는 시간과 여러 GB의 공간이 필요할 수 있다.

설치 대상은 libmutter, mutter-common, mutter-common-bin, GIR의 4개 패키지다. 디버그·개발·시험 패키지는 설치하지 않는다. 기본 버전이면 저장소의 공식 원복 패키지를 복사하고, 다른 버전이면 APT에서 동일 기준 버전의 원복 패키지까지 받아 산출물을 완성한다. 해당 버전이 저장소에서 사라졌다면 이 단계를 강제로 건너뛰지 말고 구할 수 있는 공식 소스/패키지 버전을 맞춘다.

## 같은 Ubuntu의 새 공식 소스로 재적용

APT의 소스 저장소를 활성화하고 현재 공식 소스와 그 DSC가 가리키는 tarball들을 함께 확보한다. libinput은 현재 설치된 `libinput10`과 같은 소스 버전을 사용한다. Mutter는 GNOME 50용 소스를 사용한다. 버전 비교와 공식 패치 포함 여부를 먼저 검토한다.

```bash
# 실제 확보한 DSC 경로로 바꾼다. 기존 빌드 폴더와 다른 새 경로 사용.
./build-custom prepare drag --dsc /path/to/libinput_VERSION.dsc --workdir build/drag-updated
./build-custom build drag --workdir build/drag-updated
./ubuntu-custom install drag --artifacts build/drag-updated/artifacts --dry-run

./build-custom prepare mutter --dsc /path/to/mutter_VERSION.dsc --workdir build/mutter-updated
./build-custom deps mutter --workdir build/mutter-updated
./build-custom build mutter --workdir build/mutter-updated
./ubuntu-custom install mutter --artifacts build/mutter-updated/artifacts --dry-run
```

외부 DSC는 신뢰할 수 있는 Ubuntu 경로에서 확보한다. 도구는 적용 가능/이미 적용됨/충돌을 구분하고 fuzz 없이 적용한다. `already-applied`이면 공식 수정이 들어갔는지 검토하고 중복 패치를 빌드하지 않는다. `conflict`이면 사람이 새 코드에 맞춰 검토해야 한다. Ubuntu 메이저 업그레이드나 GNOME 51 이상은 의존성과 라이브러리 API가 달라질 수 있으므로 이 레시피의 자동 적용 범위 밖이다.

빌드 결과는 설치 전까지 현재 시스템에 영향을 주지 않는다. 성공한 산출물을 계속 보관할 때는 `artifacts/` 아래 새 버전 디렉터리에 복사하고 검증 환경·시험 결과·해시를 함께 남긴다. 기존에 검증한 보관 바이너리를 조용히 덮어쓰지 않는다.
