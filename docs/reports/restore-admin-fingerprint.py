#!/usr/bin/python3
import hashlib
import json
import os
import tempfile
from pathlib import Path

if os.geteuid() != 0:
    os.execvp('pkexec', ['pkexec', '/usr/bin/python3', str(Path(__file__).resolve())])
backup = Path('/var/lib/local-fingerprint-auth/2026-09-19')
manifest = json.loads((backup / 'manifest.json').read_text())
actions = []
for name in ('sudo', 'sudo-i', 'polkit-1'):
    path = Path('/etc/pam.d') / name
    if not path.exists() and name == 'polkit-1':
        continue
    current = hashlib.sha256(path.read_bytes()).hexdigest()
    if name != 'polkit-1' and current == manifest[name]['sha256']:
        continue
    if current != manifest[name]['new_sha256']:
        raise SystemExit(f'{path} changed after installation. Review it before restoring.')
    if name != 'polkit-1':
        data = (backup / (name + '.original')).read_bytes()
        assert hashlib.sha256(data).hexdigest() == manifest[name]['sha256']
    else:
        data = None
    actions.append((path, data))
for path, data in actions:
    if data is None:
        path.unlink()
        continue
    fd, temporary = tempfile.mkstemp(prefix='.restore-fingerprint-', dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
print('Original sudo and polkit authentication restored. Fingerprint enrollment is unchanged.')
