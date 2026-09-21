#!/usr/bin/python3
"""Prepare or rebuild archived sources. Never installs into the running system."""
import argparse
import email.utils
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from common import (REPO, atomic_write, check_rebuild_host, clean_env, digest, host, load_artifact,
                    load_artifact_catalog, output, run, safe_path, version_slug)
from manage import verify_repository

PATCHES = {'drag': 'drag-only.patch', 'mutter': 'mutter-keymap-race.patch'}
SOURCE_NAMES = {'drag': 'libinput', 'mutter': 'mutter'}
SOURCE_PACKAGES = {'drag': 'libinput', 'mutter': 'mutter'}
BASE_DEPS = 'build-essential meson ninja-build pkg-config dpkg-dev patch'
DEPS = {
    'fingerprint': 'libglib2.0-dev libgusb-dev libssl-dev libudev-dev libcairo2-dev',
    'drag': 'libevdev-dev libudev-dev libwacom-dev libmtdev-dev libinput-dev check python3-pytest libsystemd-dev',
}
REQUIRED_COMMANDS = {
    'fingerprint': ['meson', 'ninja', 'pkg-config', 'cc', 'patch'],
    'drag': ['meson', 'ninja', 'pkg-config', 'cc', 'patch', 'dpkg-source'],
    'mutter': ['dpkg-buildpackage', 'dpkg-source', 'patch', 'meson', 'ninja'],
}


def unpack(archive, dest):
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as f:
        f.extractall(dest, filter='data')


def patch_state(src, patch):
    cmd = ['patch', '--batch', '--fuzz=0', '-p1', '--dry-run', '-i', patch]
    if subprocess.run([str(x) for x in cmd + ['--forward']], cwd=src,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return 'applicable'
    if subprocess.run([str(x) for x in cmd + ['--reverse']], cwd=src,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return 'already-applied'
    return 'conflict'


def source_version(src):
    return output(['dpkg-parsechangelog', '-l', src / 'debian/changelog', '-S', 'Version'])


def prepare(args, work):
    marker = work / 'prepared.json'
    if marker.exists():
        meta = json.loads(marker.read_text())
        if meta['component'] != args.component:
            raise ValueError('Work directory belongs to another component')
        if args.dsc and str(args.dsc.resolve()) != meta.get('dsc'):
            raise ValueError('Use a new --workdir for a different source')
        return meta
    if work.exists() and any(work.iterdir()):
        raise ValueError('Incomplete work directory exists; choose another --workdir')
    verify_repository()
    work.mkdir(parents=True, exist_ok=True)
    src = work / 'source'
    meta = {'component': args.component, **host()}
    if args.component == 'fingerprint':
        if args.dsc:
            raise ValueError('--dsc applies only to drag and mutter')
        unpack(REPO / 'sources/fingerprint/libfprint-e105528.tar.gz', work / 'unpack')
        (work / 'unpack/libfprint-e105528').rename(src)
        meta['base_version'] = '1.94.9-e105528'
    else:
        dsc = args.dsc or next((REPO / 'sources' / args.component).glob('*.dsc'))
        dsc = dsc.resolve()
        # dpkg-source checks the source files against the DSC checksums.
        run(['dpkg-source', '-x', dsc, src], env=clean_env())
        if output(['dpkg-parsechangelog', '-l', src / 'debian/changelog', '-S', 'Source']) != SOURCE_NAMES[args.component]:
            raise ValueError('Wrong source package')
        meta.update(base_version=source_version(src), dsc=str(dsc))
        patch = REPO / 'patches' / PATCHES[args.component]
        state = patch_state(src, patch)
        if state != 'applicable':
            raise ValueError(f'Patch state: {state}. Review the current source; no automatic forced patching.')
        if args.component == 'drag':
            run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', patch], cwd=src)
            unpack(REPO / 'sources/drag/enable-3fg-drag-09e9ca7.tar.gz', work / 'shim-source')
        else:
            if not re.match(r'(?:\d+:)?50\.', meta['base_version']):
                raise ValueError('Mutter recipe supports GNOME 50 only; review the new API and package names')
            if '+keymapfix' in meta['base_version']:
                raise ValueError('Supply unmodified Ubuntu source, not an earlier local build')
            name = 'ubuntu-custom-keymap-race.patch'
            shutil.copy2(patch, src / 'debian/patches' / name)
            series = src / 'debian/patches/series'
            series.write_text(series.read_text().rstrip() + '\n' + name + '\n')
            run(['dpkg-source', '--before-build', src], env=clean_env())
            meta['version'] = meta['base_version'] + '+keymapfix1'
            changelog = src / 'debian/changelog'
            entry = (f'mutter ({meta["version"]}) UNRELEASED; urgency=medium\n\n'
                     '  * Backport upstream 709ef343: access XKB only in the input thread.\n\n'
                     f' -- Ubuntu Custom <local@localhost>  {email.utils.formatdate(localtime=True)}\n\n')
            changelog.write_text(entry + changelog.read_text())
    atomic_write(marker, json.dumps(meta, indent=2) + '\n')
    print(f'Prepared source: {src}', flush=True)
    return meta


def dependency_packages(component):
    return BASE_DEPS.split() + DEPS.get(component, '').split()


def dependencies(args, work):
    # Print-only: dependency installation is a separate, explicit action.
    print(shlex.join(['sudo', 'apt-get', 'install', *dependency_packages(args.component)]))
    if args.component == 'mutter':
        if not (work / 'prepared.json').exists():
            print('First run: ./build-custom prepare mutter')
        else:
            print(shlex.join(['sudo', 'apt-get', '--no-install-recommends', 'build-dep', str(work / 'source')]))


def missing_build_tools(component):
    missing = []
    for name in REQUIRED_COMMANDS[component]:
        if not shutil.which(name, path=clean_env()['PATH']):
            missing.append(name)
    for package in dependency_packages(component):
        status = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', package],
                                text=True, capture_output=True)
        if status.returncode != 0 or status.stdout.strip() != 'installed':
            missing.append(package)
    return missing


def showsrc_files(package, version):
    """Return [(filename, sha256), ...] for one Ubuntu source version."""
    text = output(['apt-cache', 'showsrc', package], env=clean_env())
    for block in text.split('\n\n'):
        ver = None
        for line in block.splitlines():
            if line.startswith('Version: '):
                ver = line.split(': ', 1)[1]
                break
        if ver != version:
            continue
        files = []
        in_sha = False
        for line in block.splitlines():
            if line.startswith('Checksums-Sha256:'):
                in_sha = True
                continue
            if in_sha:
                if not line.startswith(' '):
                    break
                parts = line.split()
                if len(parts) >= 3:
                    files.append((parts[-1], parts[0]))
        if files:
            return files
    raise ValueError(f'No apt source metadata for {package}={version}')


def fetch_ubuntu_source(package, version, dest):
    """Download DSC + tarballs via apt-get source, with Launchpad file fallback."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    env = clean_env()
    attempted = subprocess.run(
        ['apt-get', 'source', '--download-only', f'{package}={version}'],
        cwd=dest, env=env, text=True, capture_output=True)
    preferred = [p for p in dest.glob(f'{package}_*.dsc')
                 if p.name == f'{package}_{version}.dsc' or version_slug(version) in p.name]
    if attempted.returncode == 0 and preferred:
        return preferred[0].resolve()

    print(f'apt-get source failed for {package}={version}; trying Launchpad file downloads.', flush=True)
    try:
        files = showsrc_files(package, version)
    except ValueError as exc:
        detail = (attempted.stderr or attempted.stdout).strip()
        raise ValueError(f'{exc}; apt-get source failed: {detail}. '
                         'Enable Ubuntu source repositories or supply a trusted DSC with build-custom prepare.') from exc
    for name, sha in files:
        if Path(name).name != name:
            raise ValueError(f'Invalid source filename: {name}')
        target = safe_path(dest, name)
        if target.is_file() and digest(target) == sha:
            continue
        url = f'https://launchpad.net/ubuntu/+archive/primary/+files/{name}'
        print(f'Downloading {name}', flush=True)
        run(['curl', '-fsSL', '-o', target, url], env=env)
        if digest(target) != sha:
            raise ValueError(f'Checksum mismatch after download: {name}')
    dsc_names = [name for name, _ in files if name.endswith('.dsc')]
    if len(dsc_names) != 1:
        raise ValueError(f'Expected one DSC for {package}={version}')
    dsc_name = dsc_names[0]
    dsc = dest / dsc_name
    if not dsc.is_file():
        raise ValueError(f'Missing DSC after download for {package}={version}')
    return dsc.resolve()


def auto_workdir(component, base_version):
    return REPO / 'build' / f'{component}-auto-{version_slug(base_version)}'


def source_cache_dir(component, base_version):
    return REPO / 'build' / 'source-cache' / component / version_slug(base_version)


def rebuild_component(component, base_version, jobs=None):
    """Fetch matching Ubuntu source, prepare, and build artifacts for this host."""
    if component not in ('drag', 'mutter'):
        raise ValueError(f'Automatic rebuild is not supported for {component}')
    check_rebuild_host()
    jobs = jobs or min(os.cpu_count() or 2, 8)
    work = auto_workdir(component, base_version)
    dest = work / 'artifacts'
    if (dest / 'manifest.json').is_file():
        existing = load_artifact(dest, component)
        if existing.get('base_version') == base_version:
            print(f'Reusing previous rebuild artifacts: {dest}', flush=True)
            return dest, existing
        raise ValueError(f'Work directory has unrelated artifacts: {work}')
    if os.geteuid() == 0:
        raise ValueError('Build as a regular user; do not run this tool with sudo')
    missing = missing_build_tools(component)
    if missing:
        cmd = shlex.join(['sudo', 'apt-get', 'install', *dependency_packages(component)])
        raise ValueError(f'Missing build tools/packages: {", ".join(missing)}. Install with: {cmd}')
    if work.exists() and (work / 'prepared.json').exists():
        meta = json.loads((work / 'prepared.json').read_text())
        if meta.get('base_version') != base_version or meta.get('component') != component:
            raise ValueError(f'Use a clean workdir; refusing to reuse {work}')
    else:
        if work.exists() and any(work.iterdir()):
            raise ValueError(f'Incomplete work directory exists; remove or rename {work}')
        # prepare() requires an empty workdir; keep downloaded sources in a
        # separate cache so a retry can reuse them without changing the build.
        dsc = fetch_ubuntu_source(SOURCE_PACKAGES[component], base_version,
                                  source_cache_dir(component, base_version))
        args = argparse.Namespace(component=component, dsc=dsc, workdir=work, jobs=jobs)
        meta = prepare(args, work)
        if meta['base_version'] != base_version:
            raise ValueError(f'Prepared version {meta["base_version"]} != requested {base_version}')
    args = argparse.Namespace(component=component, dsc=None, workdir=work, jobs=jobs)
    if component == 'mutter':
        print(shlex.join(['sudo', 'apt-get', '--no-install-recommends', 'build-dep', str(work / 'source')]),
              flush=True)
        check = subprocess.run(['dpkg-checkbuilddeps', str(work / 'source' / 'debian/control')],
                               text=True, capture_output=True, env=clean_env())
        if check.returncode != 0:
            detail = (check.stderr or check.stdout or 'unmet build dependencies').strip()
            raise ValueError(f'Mutter build dependencies missing: {detail}')
        build_mutter(args, work, meta)
    else:
        build_library(args, work, meta)
    return dest, load_artifact(dest, component)


def finish_artifact(dest, meta):
    meta['schema'] = 1
    meta['files'] = {str(p.relative_to(dest)): digest(p) for p in sorted(dest.rglob('*'))
                     if p.is_file() and p.name != 'manifest.json'}
    atomic_write(dest / 'manifest.json', json.dumps(meta, indent=2) + '\n')
    print(f'\nBuilt artifacts: {dest}\nInspect, then install with:\n' + shlex.join(
        [str(REPO / 'ubuntu-custom'), 'install', meta['component'], '--artifacts', str(dest), '--dry-run']))


def build_library(args, work, meta):
    src, out = work / 'source', work / 'meson-build'
    env = clean_env()
    component = args.component
    options = ['--prefix=/usr', '--libdir=lib']
    if component == 'fingerprint':
        options += ['--buildtype=debugoptimized', '-Ddrivers=egismoc', '-Dintrospection=false',
                    '-Dudev_rules=disabled', '-Dudev_hwdb=disabled', '-Dgtk-examples=false',
                    '-Ddoc=false', '-Dinstalled-tests=false']
    else:
        options += ['--buildtype=release', '-Dudev-dir=/usr/lib/udev', '-Dlibwacom=true',
                    '-Dmtdev=true', '-Ddebug-gui=false', '-Dtests=true', '-Ddocumentation=false',
                    '-Dlua-plugins=disabled']
    if not (out / 'build.ninja').exists():
        run(['meson', 'setup', out, src, *options], env=env)
    run(['meson', 'compile', '-C', out, '-j', args.jobs], env=env)
    # The private egismoc build does not install hwdb or AppStream data.
    # Run its four library unit-test groups, as in the original validated build.
    tests = ['--suite', 'unit-tests'] if component == 'fingerprint' else [
        'leftover-rules', 'validate-quirks', 'validate-quirks-files', 'tools-builddir-lookup',
        'tools-builddir-lookup-installed', 'symbols-leak-test',
        'test-library-version', 'test-utils', 'libinput-test-deviceless']
    if component == 'drag':
        names = {t['name'] for t in json.loads((out / 'meson-info/intro-tests.json').read_text())}
        if 'test-litest-selftest' in names:
            tests.append('test-litest-selftest')
        else:
            print('Optional litest self-test unavailable: install check and reconfigure Meson to enable it.', flush=True)
    run(['meson', 'test', '-C', out, '--print-errorlogs', *tests], env=env)
    stage = work / 'stage'
    run(['meson', 'install', '-C', out, '--destdir', stage], env=env)
    glob = 'libfprint-2.so.*' if component == 'fingerprint' else 'libinput.so.*'
    libraries = [p for p in stage.rglob(glob) if p.is_file() and not p.is_symlink()]
    if len(libraries) != 1:
        raise ValueError(f'Expected exactly one staged {glob}')
    lib = libraries[0]
    soname = re.search(r'\(SONAME\).*\[([^]]+)\]', output(['readelf', '-d', lib])).group(1)
    dest = work / 'artifacts'
    dest.mkdir(exist_ok=True)
    shutil.copy2(lib, dest / lib.name)
    manifest = {**host(), 'component': component, 'library': lib.name, 'soname': soname}
    if component == 'fingerprint':
        manifest.update(version='e105528', usb_id='1c7a:05b1',
                        source_commit='e105528828a04dffde789cda48742c204183386d')
    else:
        shim = 'libenable-3fg-drag.so'
        flags = shlex.split(output(['pkg-config', '--cflags', 'libinput']))
        run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', '-fPIC', *flags, '-shared',
             '-Wl,-z,relro,-z,now,-z,noexecstack', '-o', dest / shim,
             work / 'shim-source/enable-3fg-drag-09e9ca7/enable-3fg-drag.c', '-ldl'], env=env)
        manifest.update(version=meta['base_version'] + '+dragonly1', base_version=meta['base_version'],
                        shim=shim, shim_commit='09e9ca763eca05c33a183c7a6cf582bdd77dbbb1')
    finish_artifact(dest, manifest)


def build_mutter(args, work, meta):
    env = clean_env()
    runtime = work / 'runtime'
    runtime.mkdir(exist_ok=True, mode=0o700)
    runtime.chmod(0o700)
    # Inherited x11-only GDK_BACKEND made Wayland tests fail in the original build.
    env.update(XDG_RUNTIME_DIR=str(runtime), GSETTINGS_BACKEND='memory')
    env.pop('DEB_BUILD_OPTIONS', None)  # Never inherit a caller's nocheck.
    env.pop('DEB_BUILD_PROFILES', None)
    run(['dpkg-buildpackage', '-us', '-uc', '-b', f'-j{args.jobs}'], cwd=work / 'source', env=env)
    dest = work / 'artifacts'
    for name in ('patched', 'stock'):
        (dest / name).mkdir(parents=True, exist_ok=True)
    packages = ['libmutter-18-0', 'mutter-common', 'mutter-common-bin', 'gir1.2-mutter-18']
    stock_catalog = load_artifact_catalog('mutter')
    entries = []
    for package in packages:
        matches = []
        for deb in work.glob('*.deb'):
            if output(['dpkg-deb', '-f', deb, 'Package']) == package:
                matches.append(deb)
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one built package: {package}')
        deb = matches[0]
        shutil.copy2(deb, dest / 'patched' / deb.name)
        # Archive rollback packages of the same official source version.
        stock_copied = False
        for folder, bundled in stock_catalog:
            if bundled.get('base_version') != meta['base_version']:
                continue
            entry = next(e for e in bundled['packages'] if e['package'] == package)
            stock = folder / entry['stock']
            shutil.copy2(stock, dest / 'stock' / stock.name)
            stock_copied = True
            break
        if not stock_copied:
            run(['apt-get', 'download', f'{package}={meta["base_version"]}'], cwd=dest / 'stock', env=env)
        stocks = [p for p in (dest / 'stock').glob('*.deb')
                  if output(['dpkg-deb', '-f', p, 'Package']) == package]
        if len(stocks) != 1 or output(['dpkg-deb', '-f', stocks[0], 'Version']) != meta['base_version']:
            raise ValueError(f'Missing matching stock rollback package: {package}')
        entries.append({'package': package, 'patched': 'patched/' + deb.name, 'stock': 'stock/' + stocks[0].name})
    finish_artifact(dest, {**host(), 'component': 'mutter', 'version': meta['version'],
                          'base_version': meta['base_version'], 'shell_major': 50, 'packages': entries,
                          'source_commit': '709ef34381e51e83327b9c6d7270ed437d714768'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['deps', 'prepare', 'build'])
    p.add_argument('component', choices=['fingerprint', 'drag', 'mutter'])
    p.add_argument('--dsc', type=Path, help='Trusted Ubuntu DSC and matching source tarballs, for rebasing')
    p.add_argument('--workdir', type=Path, help='New empty build directory (default: build/COMPONENT)')
    p.add_argument('--jobs', type=int, default=min(os.cpu_count() or 2, 8))
    args = p.parse_args()
    if args.jobs < 1:
        p.error('--jobs must be positive')
    if os.geteuid() == 0:
        p.error('Build as a regular user; do not run this tool with sudo')
    if host()['distro'] != 'ubuntu' or host()['release'] != '26.04':
        p.error('Recipes are validated for Ubuntu 26.04; review dependencies before porting to a new release')
    work = (args.workdir or REPO / 'build' / args.component).resolve()
    if args.action == 'deps':
        dependencies(args, work)
        return
    meta = prepare(args, work)
    if args.action == 'build':
        if args.component == 'mutter':
            build_mutter(args, work, meta)
        else:
            build_library(args, work, meta)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
