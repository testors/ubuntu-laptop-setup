"""Shared, dependency-free helpers. No host changes on import."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def output(args, **kwargs):
    return run(args, text=True, stdout=subprocess.PIPE, **kwargs).stdout.strip()


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def safe_path(folder, name):
    p = folder / name
    if Path(name).is_absolute() or not p.resolve().is_relative_to(folder.resolve()):
        raise ValueError(f'Path escapes artifact directory: {name}')
    return p


def load_artifact(folder, component=None):
    folder = Path(folder).resolve()
    m = json.loads((folder / 'manifest.json').read_text())
    if m['schema'] != 1 or (component and m['component'] != component):
        raise ValueError('Unexpected artifact manifest')
    for name, expected in m['files'].items():
        if digest(safe_path(folder, name)) != expected:
            raise ValueError(f'Checksum mismatch: {name}')
    roles = [m[k] for k in ('library', 'shim') if k in m]
    roles += [e[k] for e in m.get('packages', []) for k in ('patched', 'stock')]
    if not all(name in m['files'] for name in roles):
        raise ValueError('Unverified file referenced by manifest')
    for k in ('library', 'shim', 'soname'):
        if k in m and Path(m[k]).name != m[k]:
            raise ValueError(f'{k} must be a filename')
    return m


def host():
    release = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            release[k] = v.strip('"')
    return {'distro': release['ID'], 'release': release['VERSION_ID'],
            'architecture': output(['dpkg', '--print-architecture'])}


def compatible(m, current=None):
    current = current or host()
    for k in ('distro', 'release', 'architecture'):
        if current[k] != m[k]:
            raise ValueError(f'{k}: artifact={m[k]}, host={current[k]}; rebuild for this host')


def clean_env():
    env = os.environ.copy()
    # Use distro tools, not an IDE's bundled Python/compiler wrappers.
    env['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    for k in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'GDK_BACKEND', 'DISPLAY',
              'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(k, None)
    return env


def atomic_write(path, data, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.ubuntu-custom-', dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as f:
            f.write(data if isinstance(data, bytes) else data.encode())
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def symlink(path, target):
    temporary = path.with_name(path.name + '.ubuntu-custom-new')
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(target)
    os.replace(temporary, path)


def package_version(name):
    r = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status} ${Version}', name],
                       text=True, capture_output=True)
    return r.stdout.split(' ', 1)[1] if r.returncode == 0 and r.stdout.startswith('installed ') else None


def newer(a, b):
    return subprocess.run(['dpkg', '--compare-versions', a, 'gt', b]).returncode == 0
