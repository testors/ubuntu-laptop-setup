#!/usr/bin/python3
"""Enable fingerprint-first sudo/polkit authentication with password fallback."""
import argparse
import ctypes
import difflib
import hashlib
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PAM = Path('/etc/pam.d')
VENDOR = Path('/usr/lib/pam.d/polkit-1')
STATE = Path('/var/lib/ubuntu-custom/admin-fingerprint')
NAMES = ('sudo', 'sudo-i', 'polkit-1')
RULE = 'auth sufficient pam_fprintd.so max-tries=1 timeout=10\n'
BLOCK = '# ubuntu-custom: admin-fingerprint\n' + RULE + '# end ubuntu-custom: admin-fingerprint\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=0o644):
    fd, tmp = tempfile.mkstemp(prefix='.admin-fingerprint-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as f:
            f.write(data if isinstance(data, bytes) else data.encode())
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_policy(path):
    if path.is_symlink():
        raise ValueError(f'Refusing symlinked PAM policy: {path}')
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f'Not a regular PAM policy: {path}')
    return path.read_bytes()


def polkit_policy():
    return ('#%PAM-1.0\n' + BLOCK +
            '# Follow the distribution policy for all remaining PAM operations.\n' +
            ''.join(f'{kind} include {VENDOR}\n' for kind in ('auth', 'account', 'password', 'session'))).encode()


def sudo_policy(data):
    text = data.decode()
    if text.count(BLOCK) > 1:
        raise ValueError('Duplicate local fingerprint block')
    text = text.replace(BLOCK, '')
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    auth = [line for line in lines if line.startswith(('auth ', 'auth\t', '-auth ', '-auth\t', '@include'))]
    standard_includes = {'@include common-auth', '@include common-account', '@include common-password',
                         '@include common-session', '@include common-session-noninteractive'}
    if auth.count('@include common-auth') != 1 or any(
            line.startswith(('auth ', 'auth\t', '-auth ', '-auth\t')) or
            (line.startswith('@include') and line not in standard_includes) for line in auth):
        raise ValueError('Nonstandard sudo authentication policy; review instead of overwriting')
    if 'pam_fprintd' in text:
        raise ValueError('Another fingerprint rule already exists')
    return text.replace('@include common-auth', BLOCK + '@include common-auth', 1).encode()


def plan():
    if not VENDOR.is_file():
        raise ValueError(f'Missing distribution polkit policy: {VENDOR}')
    if 'pam_fprintd' in (PAM / 'common-auth').read_text():
        raise ValueError('common-auth already includes fingerprint authentication; review the existing policy')
    originals, prepared, modes = {}, {}, {}
    for name in NAMES:
        path = PAM / name
        old = read_policy(path)
        if name == 'polkit-1':
            new = polkit_policy()
            if old is not None and old != new:
                raise ValueError('An unrelated local polkit policy exists; refusing to replace it')
        else:
            if old is None:
                raise ValueError(f'Missing sudo policy: {path}')
            new = sudo_policy(old)
        originals[name], prepared[name] = old, new
        modes[name] = stat.S_IMODE(path.stat().st_mode) if old is not None else 0o644
    return originals, prepared, modes


def account_checks(user):
    """Load actual PAM policies and run account checks; never accept a password."""
    lib = ctypes.CDLL('libpam.so.0')
    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    @callback
    def no_prompt(count, messages, responses, data):
        return 19  # PAM_CONV_ERR
    class Conversation(ctypes.Structure):
        _fields_ = [('conv', callback), ('data', ctypes.c_void_p)]
    conv = Conversation(no_prompt, None)
    lib.pam_start.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.POINTER(ctypes.c_void_p)]
    lib.pam_acct_mgmt.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    for name in NAMES:
        handle = ctypes.c_void_p()
        result = lib.pam_start(name.encode(), user.encode(), ctypes.byref(conv), ctypes.byref(handle))
        if result != 0:
            raise ValueError(f'{name}: pam_start returned {result}')
        try:
            result = lib.pam_acct_mgmt(handle, 0)
            if result != 0:
                raise ValueError(f'{name}: pam_acct_mgmt returned {result}')
        finally:
            lib.pam_end(handle, result)
        print(f'{name}: PAM parser/account checks passed', flush=True)


def install(args):
    originals, prepared, modes = plan()
    changed = [name for name in NAMES if originals[name] != prepared[name]]
    for name in changed:
        print(''.join(difflib.unified_diff((originals[name] or b'').decode().splitlines(True),
                                          prepared[name].decode().splitlines(True),
                                          fromfile=str(PAM / name), tofile=str(PAM / name))), end='')
    if not changed:
        print('Already enabled; no changes.')
        return
    if args.dry_run:
        print('DRY RUN: PAM files and services are unchanged.')
        return
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE.chmod(0o700)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-'), dir=STATE))
    manifest = {'schema': 1, 'files': {name: {
        'original_sha256': sha(originals[name]) if originals[name] is not None else None,
        'installed_sha256': sha(prepared[name]), 'mode': modes[name]} for name in NAMES}}
    for name in NAMES:
        if originals[name] is not None:
            atomic_write(backup / (name + '.original'), originals[name], 0o600)
    atomic_write(backup / 'manifest.json', json.dumps(manifest, indent=2) + '\n', 0o600)
    # Standalone root-owned recovery copy, independent of the user's repository.
    atomic_write(backup / 'restore.py', Path(__file__).read_bytes(), 0o700)
    written = []
    try:
        for name in changed:
            atomic_write(PAM / name, prepared[name], modes[name])
            written.append(name)
        account_checks(args.user)
        atomic_write(STATE / 'state.json', json.dumps({'backup': str(backup)}) + '\n', 0o600)
    except BaseException:
        for name in reversed(written):
            if originals[name] is None:
                (PAM / name).unlink(missing_ok=True)
            else:
                atomic_write(PAM / name, originals[name], modes[name])
        print('Installation failed; previous PAM policies restored.', file=sys.stderr)
        raise
    print(f'Enabled sudo, sudo-i and polkit-1; backup: {backup}\nEffective on the next authentication; no restart required.')


def rollback(args):
    backup = (args.backup or Path(json.loads((STATE / 'state.json').read_text())['backup'])).resolve()
    if not backup.is_relative_to(STATE.resolve()) or backup == STATE.resolve():
        raise ValueError('Backup is outside the protected state directory')
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest['schema'] != 1 or set(manifest['files']) != set(NAMES):
        raise ValueError('Unexpected backup manifest')
    actions = []
    for name in NAMES:
        entry = manifest['files'][name]
        current = read_policy(PAM / name)
        current_sha = sha(current) if current is not None else None
        if current_sha == entry['original_sha256']:
            continue
        if current_sha != entry['installed_sha256']:
            raise ValueError(f'{name} changed after installation; refusing to discard later edits')
        original = (backup / (name + '.original')).read_bytes() if entry['original_sha256'] else None
        if original is not None and sha(original) != entry['original_sha256']:
            raise ValueError(f'Corrupt backup: {name}')
        actions.append((name, original, entry['mode']))
    print('Restore original policies:', ', '.join(name for name, _, _ in actions) or 'already restored')
    if args.dry_run:
        return
    for name, data, mode in actions:
        if data is None:
            (PAM / name).unlink()
        else:
            atomic_write(PAM / name, data, mode)
    print('Restored; fingerprint driver and enrollment retained.')


def status():
    for name in NAMES:
        data = read_policy(PAM / name)
        enabled = data is not None and BLOCK.encode() in data
        print(f'{name}: ' + ('fingerprint first, password fallback (10 seconds)' if enabled else 'not enabled by this tool'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['install', 'rollback', 'status'])
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--backup', type=Path, help='Specific protected backup directory for rollback')
    p.add_argument('--user', default=pwd.getpwuid(int(os.environ.get('PKEXEC_UID', os.environ.get('SUDO_UID', os.getuid())))).pw_name)
    args = p.parse_args()
    pwd.getpwnam(args.user)
    if args.action == 'status':
        status()
        return
    if args.action == 'install':
        os_release = Path('/etc/os-release').read_text()
        if 'ID=ubuntu\n' not in os_release or 'VERSION_ID="26.04"' not in os_release:
            raise ValueError('PAM recipe is validated for Ubuntu 26.04; review this distribution before porting')
        if not list(Path('/usr/lib').glob('*/security/pam_fprintd.so')) and not Path('/usr/lib/security/pam_fprintd.so').exists():
            raise ValueError('Install libpam-fprintd first')
    if os.geteuid() != 0 and not (args.action == 'install' and args.dry_run):
        command = ['pkexec', '/usr/bin/python3'] if shutil.which('pkexec') and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')) else ['sudo', '/usr/bin/python3']
        argv = [str(Path(__file__).resolve()), args.action, '--user', args.user]
        if args.dry_run:
            argv.append('--dry-run')
        if args.backup:
            argv += ['--backup', str(args.backup.resolve())]
        os.execvp(command[0], command + argv)
    if args.action == 'install':
        install(args)
    else:
        rollback(args)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
