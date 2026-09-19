#!/usr/bin/python3
"""Inspect, install and undo the archived customizations; no automatic logout."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from common import (REPO, atomic_write, clean_env, compatible, digest, host,
                    load_artifact, newer, output, package_version, run, symlink)

ROOT_STATE = Path('/var/lib/ubuntu-custom')
FP_CONFIG = Path('/etc/systemd/system/fprintd.service.d/60-egis-05b1.conf')
SERVICE = 'org.gnome.Shell@ubuntu.service'


def user_paths(service):
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config'))
    state = Path(os.environ.get('XDG_STATE_HOME', home / '.local/state'))
    if not config.is_absolute() or not state.is_absolute():
        raise ValueError('XDG paths must be absolute')
    return (home / '.local/lib/ubuntu-custom/drag',
            config / 'systemd/user' / (service + '.d') / '60-three-finger-drag.conf',
            state / 'ubuntu-custom/drag')


def env_line(name, value):
    if any(c.isspace() for c in value) or ':' in value:
        raise ValueError('Library paths must not contain whitespace or colon')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return f'Environment="{name}={value}"\n'


def fp_config(folder):
    return '# ubuntu-custom: fingerprint\n[Service]\n' + env_line('LD_LIBRARY_PATH', str(folder))


def drag_config(folder, m):
    return ('# ubuntu-custom: drag\n[Service]\n' +
            env_line('LD_PRELOAD', str(folder / m['shim'])) +
            env_line('LD_LIBRARY_PATH', str(folder)))


def legacy_configs(component):
    if component == 'fingerprint':
        return ['[Service]\nEnvironment="LD_LIBRARY_PATH=/opt/fingerprint-egis-05b1/e105528/lib"\n']
    h = Path.home()
    text = ('# Enable libinput native three-finger drag for this user\'s Ubuntu GNOME session.\n'
            '[Service]\n' + env_line('LD_PRELOAD', str(h / '.local/lib/enable-3fg-drag/09e9ca7/libenable-3fg-drag.so')))
    return [text, text + env_line('LD_LIBRARY_PATH', str(h / '.local/lib/enable-3fg-drag/libinput-1.31.1-drag-only-v1'))]


def state_read(folder):
    try:
        return json.loads((folder / 'state.json').read_text())
    except (FileNotFoundError, PermissionError):
        return {}


def managed_config(path, component, state, expected):
    if not path.exists():
        return
    data = path.read_text()
    if data == expected or data in legacy_configs(component):
        return
    if hashlib.sha256(data.encode()).hexdigest() == state.get('config_sha256'):
        return
    raise ValueError(f'Unrecognized existing configuration; refusing to overwrite: {path}')


def linker_check(binary, folder, shim=None):
    env = clean_env()
    env['LD_LIBRARY_PATH'] = str(folder)
    if shim:
        env['LD_PRELOAD'] = str(folder / shim)
    r = run(['ldd', '-r', binary], env=env, text=True, capture_output=True)
    text = r.stdout + r.stderr
    if 'not found' in text or 'undefined symbol:' in text:
        raise ValueError('Dynamic linking failed:\n' + text)


def stage_libraries(folder, artifacts, m):
    folder.mkdir(parents=True, exist_ok=True)
    for name in m['files']:
        if '/' in name:
            raise ValueError('Library artifact must contain flat filenames')
        atomic_write(folder / name, (artifacts / name).read_bytes())
    symlink(folder / m['soname'], m['library'])


def usb_present(usb_id):
    for p in Path('/sys/bus/usb/devices').glob('*'):
        try:
            if (p / 'idVendor').read_text().strip() + ':' + (p / 'idProduct').read_text().strip() == usb_id:
                return True
        except FileNotFoundError:
            pass
    return False


def apply_libraries(args, m, artifacts):
    component = args.component
    key = m['files'][m['library']][:16]
    if component == 'fingerprint':
        if not usb_present(m['usb_id']):
            raise ValueError(f'This driver requires USB sensor {m["usb_id"]}')
        binary = next((str(p) for p in [Path('/usr/libexec/fprintd'), Path('/usr/lib/fprintd/fprintd')] if p.exists()), None)
        if not binary:
            raise ValueError('Install fprintd and libpam-fprintd first')
        folder = Path('/opt/ubuntu-custom/fingerprint') / key / 'lib'
        config, state_dir = FP_CONFIG, ROOT_STATE / component
        text = fp_config(folder)
        commands = [['systemctl', 'daemon-reload'], ['systemctl', 'restart', 'fprintd.service']]
    else:
        if os.geteuid() == 0:
            raise ValueError('Install drag as the desktop user, without sudo')
        if package_version('libinput10') != m['base_version']:
            raise ValueError('System libinput10 differs from the artifact base; rebuild from the matching current source')
        if output(['systemctl', '--user', 'show', args.service, '-p', 'LoadState', '--value']) != 'loaded':
            raise ValueError('GNOME user service is unavailable; select the correct --service')
        base, config, state_dir = user_paths(args.service)
        folder = base / key
        binary = '/usr/bin/gnome-shell'
        text = drag_config(folder, m)
        commands = [['systemctl', '--user', 'daemon-reload']]
    state = state_read(state_dir)
    managed_config(config, component, state, text)
    print(f'{component}: stage {folder}; write {config}', flush=True)
    if args.dry_run:
        print('DRY RUN: no files, services or packages changed')
        return
    old = config.read_bytes() if config.exists() else None
    stage_libraries(folder, artifacts, m)
    linker_check(binary, folder, m.get('shim'))
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_dir.chmod(0o700)
    if old is not None and not (state_dir / 'previous.conf').exists():
        atomic_write(state_dir / 'previous.conf', old, 0o600)
    try:
        atomic_write(config, text)
        for cmd in commands:
            run(cmd)
        if component == 'fingerprint':
            devices = output(['busctl', 'call', 'net.reactivated.Fprint', '/net/reactivated/Fprint/Manager',
                              'net.reactivated.Fprint.Manager', 'GetDevices'])
            if devices == 'ao 0':
                raise ValueError('fprintd did not detect a sensor')
            print(devices)
    except BaseException:
        if old is None:
            config.unlink(missing_ok=True)
        else:
            atomic_write(config, old)
        for cmd in commands:
            subprocess.run(cmd, check=False)
        raise
    state = {'config_sha256': hashlib.sha256(text.encode()).hexdigest(),
             'config': str(config), 'directory': str(folder), 'manifest': m}
    atomic_write(state_dir / 'state.json', json.dumps(state, indent=2) + '\n', 0o600)
    print('Installed. ' + ('Enroll fingerprints on this machine with fprintd-enroll.' if component == 'fingerprint'
                          else 'Log out and log in to activate; the current session was not restarted.'))


def disable_libraries(args, m):
    if args.component == 'drag':
        if os.geteuid() == 0:
            raise ValueError('Disable drag as the desktop user, without sudo')
        base, config, state_dir = user_paths(args.service)
        text = drag_config(base / m['files'][m['library']][:16], m)
        commands = [['systemctl', '--user', 'daemon-reload']]
    else:
        config, state_dir = FP_CONFIG, ROOT_STATE / 'fingerprint'
        text = fp_config(Path('/opt/ubuntu-custom/fingerprint') / m['files'][m['library']][:16] / 'lib')
        commands = [['systemctl', 'daemon-reload'], ['systemctl', 'restart', 'fprintd.service']]
    managed_config(config, args.component, state_read(state_dir), text)
    print(f'Remove only the managed override: {config}')
    if args.dry_run:
        return
    if config.exists():
        config.unlink()
        for cmd in commands:
            run(cmd)
    print('Disabled; libraries and fingerprint enrollment retained. Drag requires a new login.')


def mutter_paths(folder, m, kind):
    return [folder / e[kind] for e in m['packages']]


def check_mutter_metadata(folder, m):
    major = int(m['shell_major'])
    # Other GNOME majors need a reviewed build recipe and package mapping.
    if major != 50:
        raise ValueError('This installer currently supports GNOME 50 only')
    api = 18
    expected = {f'libmutter-{api}-0', f'gir1.2-mutter-{api}', 'mutter-common', 'mutter-common-bin'}
    if {e['package'] for e in m['packages']} != expected or len(m['packages']) != 4:
        raise ValueError('Unexpected package set')
    for e in m['packages']:
        for kind, version in [('patched', m['version']), ('stock', m['base_version'])]:
            fields = dict(line.split(': ', 1) for line in output(
                ['dpkg-deb', '-f', folder / e[kind], 'Package', 'Version']).splitlines())
            if fields != {'Package': e['package'], 'Version': version}:
                raise ValueError(f'Package metadata mismatch: {e[kind]}')
    shell = output(['gnome-shell', '--version'], env=clean_env())
    if not re.search(r'\b' + str(major) + r'(?:\.|\b)', shell):
        raise ValueError(f'Wrong GNOME major version: {shell}')


def apt_install(paths, dry_run, downgrade=False):
    flags = ['--no-remove', '--reinstall'] + (['--allow-downgrades'] if downgrade else [])
    simulation = output(['apt-get', '--simulate', *flags, 'install', *paths], env=clean_env())
    print(simulation, flush=True)
    if any(line.startswith('Remv ') for line in simulation.splitlines()):
        raise ValueError('Refusing a transaction that removes packages')
    if not dry_run:
        env = clean_env()
        env.update(DEBIAN_FRONTEND='noninteractive', NEEDRESTART_MODE='l')
        run(['apt-get', '-y', *flags, 'install', *paths], env=env)


def install_mutter(args, m, artifacts):
    check_mutter_metadata(artifacts, m)
    for entry in m['packages']:
        current = package_version(entry['package'])
        if current and newer(current, m['version']):
            raise ValueError(f'{entry["package"]} {current} is newer; do not downgrade. Rebase the patch or confirm upstream fixed it.')
    if args.dry_run:
        apt_install(mutter_paths(artifacts, m, 'patched'), True)
        return
    key = hashlib.sha256(json.dumps(m, sort_keys=True).encode()).hexdigest()[:16]
    saved = ROOT_STATE / 'mutter' / key
    saved.mkdir(parents=True, exist_ok=True, mode=0o700)
    saved.parent.chmod(0o700)
    for name in m['files']:
        atomic_write(saved / name, (artifacts / name).read_bytes(), 0o600)
    atomic_write(saved / 'manifest.json', json.dumps(m, indent=2) + '\n', 0o600)
    load_artifact(saved, 'mutter')
    try:
        apt_install(mutter_paths(saved, m, 'patched'), False)
    except subprocess.CalledProcessError:
        print(f'Install incomplete. Recovery packages remain at {saved}; inspect dpkg --audit.', file=sys.stderr)
        raise
    atomic_write(saved.parent / 'state.json', json.dumps({'directory': str(saved)}) + '\n', 0o600)
    print('Mutter installed. Log out and log in to activate. No logout was requested by this program.')


def rollback_mutter(args, m, artifacts):
    state = state_read(ROOT_STATE / 'mutter')
    if state and not getattr(args, 'artifacts', None):
        saved = Path(state['directory'])
        if not saved.resolve().is_relative_to((ROOT_STATE / 'mutter').resolve()):
            raise ValueError('Invalid backup path')
        artifacts, m = saved, load_artifact(saved, 'mutter')
    else:
        print('Using verified stock packages from the selected artifact directory.')
    compatible(m)
    check_mutter_metadata(artifacts, m)
    for entry in m['packages']:
        if package_version(entry['package']) not in (m['version'], m['base_version']):
            raise ValueError('Package versions changed; refusing to downgrade an unrelated installation')
    apt_install(mutter_paths(artifacts, m, 'stock'), args.dry_run, downgrade=True)
    print('Stock package plan complete. A real rollback requires a new login to activate.')


def verify_repository():
    count = 0
    for line in (REPO / 'SHA256SUMS').read_text().splitlines():
        sha, name = line.split('  ', 1)
        p = REPO / name
        if not p.resolve().is_relative_to(REPO.resolve()) or digest(p) != sha:
            raise ValueError(f'Repository checksum mismatch: {name}')
        count += 1
    print(f'Verified {count} archived source/patch/license/artifact files')


def status(args):
    print('Host:', json.dumps(host(), ensure_ascii=False))
    for component in ('fingerprint', 'drag', 'mutter'):
        m = load_artifact(REPO / 'artifacts' / component, component)
        print(f'\n{component}: archived version {m["version"]}')
        if component == 'mutter':
            for e in m['packages']:
                print(f'  {e["package"]}: {package_version(e["package"])}')
        else:
            path = FP_CONFIG if component == 'fingerprint' else user_paths(args.service)[1]
            print('  override:', path, 'present' if path.exists() else 'MISSING')
            service_cmd = (['systemctl', 'show', 'fprintd.service'] if component == 'fingerprint'
                           else ['systemctl', '--user', 'show', args.service])
            r = subprocess.run(service_cmd + ['-p', 'Environment', '--value'], text=True, capture_output=True)
            if r.returncode == 0:
                env = dict(token.split('=', 1) for token in shlex.split(r.stdout) if '=' in token)
                folders = env.get('LD_LIBRARY_PATH', '').split(':')
                candidates = [Path(folder) / m['library'] for folder in folders if folder]
                if component == 'drag' and env.get('LD_PRELOAD'):
                    candidates += [Path(p) for p in re.split(r'[:\s]+', env['LD_PRELOAD']) if p]
                for p in candidates:
                    expected = m['files'].get(p.name)
                    match = ('matches archive' if expected and p.is_file() and digest(p) == expected
                             else 'MISSING or differs from archived binary; inspect/rebuilt version may differ')
                    print('  configured library:', p, '-', match)
                if not candidates:
                    print('  managed library environment is not active in the service configuration')
            if component == 'drag' and package_version('libinput10') != m['base_version']:
                print('  REBUILD REQUIRED: system libinput version differs from archived base')
        if component == 'fingerprint':
            print('  compatible sensor:', usb_present(m['usb_id']))
    pids = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'gnome-shell'], text=True, capture_output=True).stdout.split()
    for pid in pids:
        print(f'\nGNOME PID {pid} loaded libraries:')
        try:
            for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
                if 'r-xp' in line and any(s in line for s in ('libmutter-', 'libinput.so.', 'libenable-3fg-drag')):
                    print(' ', line.split(maxsplit=5)[-1])
                    if '(deleted)' in line:
                        print('  RELOGIN REQUIRED: the process still maps a replaced library')
        except (FileNotFoundError, PermissionError):
            pass
    from admin_fingerprint import status as admin_status
    print('\nAdministrator fingerprint PAM:')
    admin_status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'status', 'install', 'disable', 'rollback'])
    parser.add_argument('component', nargs='?', choices=['fingerprint', 'drag', 'mutter'])
    parser.add_argument('--artifacts', type=Path, help='Rebuilt artifact directory with manifest.json')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--service', default=SERVICE, help='GNOME user service used by the drag override')
    args = parser.parse_args()
    if not re.fullmatch(r'org\.gnome\.Shell@[-A-Za-z0-9_.]+\.service', args.service):
        parser.error('Invalid GNOME service name')
    if args.action == 'verify':
        verify_repository()
        return
    if args.action == 'status':
        status(args)
        return
    if not args.component:
        parser.error('Choose a component')
    if args.action == 'disable' and args.component == 'mutter':
        parser.error('Use rollback mutter')
    if args.action == 'rollback' and args.component != 'mutter':
        parser.error('Use disable fingerprint or disable drag')
    artifacts = (args.artifacts or REPO / 'artifacts' / args.component).resolve()
    m = load_artifact(artifacts, args.component)
    if args.action != 'disable':
        compatible(m)
    if args.component != 'drag' and os.geteuid() != 0 and not args.dry_run:
        program = ['pkexec', '/usr/bin/python3'] if shutil.which('pkexec') and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')) else ['sudo', '/usr/bin/python3']
        # Resolve user-supplied relative artifact paths before changing identity.
        argv = [str(Path(__file__).resolve()), args.action, args.component, '--service', args.service]
        if args.artifacts:
            argv += ['--artifacts', str(artifacts)]
        os.execvp(program[0], program + argv)
    if args.action == 'install':
        if args.component == 'mutter':
            install_mutter(args, m, artifacts)
        else:
            apply_libraries(args, m, artifacts)
    elif args.action == 'disable':
        disable_libraries(args, m)
    else:
        rollback_mutter(args, m, artifacts)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
