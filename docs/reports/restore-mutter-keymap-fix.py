#!/usr/bin/python3
"""Restore the saved official Ubuntu 26.04 Mutter packages."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

if os.geteuid() != 0:
    os.execvp('pkexec', ['pkexec', '/usr/bin/python3', str(Path(__file__).resolve())])
backup = Path('/var/lib/local-mutter-keymap-fix/50.1-0ubuntu2.4+keymapfix1')
manifest = json.loads((backup / 'manifest.json').read_text())
files = []
for entry in manifest['packages']:
    current = subprocess.check_output(
        ['/usr/bin/dpkg-query', '-W', '-f=${Version}', entry['package']], text=True)
    if current not in (manifest['version'], '50.1-0ubuntu2.4'):
        raise SystemExit(entry['package'] + ' changed since installation; review before downgrading.')
    record = entry['stock']
    assert Path(record['file']).name == record['file']
    path = backup / 'stock' / record['file']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
    files.append(str(path))
env = os.environ.copy()
env.update(DEBIAN_FRONTEND='noninteractive', NEEDRESTART_MODE='l')
subprocess.run(['/usr/bin/dpkg', '--install', *files], env=env, check=True)
print('Official Ubuntu Mutter 50.1-0ubuntu2.4 restored. Log in again to activate.')
