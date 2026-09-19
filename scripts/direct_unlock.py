#!/usr/bin/python3
"""Install the per-user GNOME extension without restarting the desktop."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from gi.repository import Gio, GLib

UUID = 'direct-unlock@testors.github.io'
SOURCE = Path(__file__).resolve().parents[1] / 'extensions' / UUID
FILES = ('metadata.json', 'extension.js', 'controller.js', 'LICENSE')
MANIFEST = 'ubuntu-custom-manifest.json'


def xdg_path(variable, fallback):
    value = os.environ.get(variable, '')
    return Path(value) if value and Path(value).is_absolute() else Path.home() / fallback


def paths():
    return (xdg_path('XDG_DATA_HOME', '.local/share') / 'gnome-shell/extensions' / UUID,
            xdg_path('XDG_STATE_HOME', '.local/state') / 'ubuntu-custom/direct-unlock')


def hashes(directory):
    result = {}
    for name in FILES:
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or symlinked extension file: {path}')
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check_existing(target):
    if target.is_symlink():
        raise ValueError(f'Refusing symlinked extension directory: {target}')
    if not target.exists():
        return None
    marker = target / MANIFEST
    if marker.is_symlink() or not marker.is_file():
        raise ValueError(f'Unmanaged extension already exists: {target}')
    manifest = json.loads(marker.read_text())
    actual = hashes(target)
    if (manifest.get('uuid') != UUID or manifest.get('files') != actual or
            {p.name for p in target.iterdir()} != set(FILES) | {MANIFEST}):
        raise ValueError(f'Installed extension has local changes; preserve/review it first: {target}')
    return actual


def configure(settings, enabled):
    keys = ('enabled-extensions', 'disabled-extensions')
    previous = {key: list(settings.get_strv(key)) for key in keys}
    desired = {key: [item for item in values if item != UUID] for key, values in previous.items()}
    desired[keys[0] if enabled else keys[1]].append(UUID)
    if any(not settings.is_writable(key) for key in keys):
        raise ValueError('GNOME extension preferences are locked by system policy')
    try:
        for key in keys:
            if desired[key] != previous[key] and not settings.set_strv(key, desired[key]):
                raise ValueError(f'Could not update {key}')
        Gio.Settings.sync()
    except BaseException:
        for key in keys:
            settings.set_strv(key, previous[key])
        Gio.Settings.sync()
        raise


def shell_info():
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync(
            'org.gnome.Shell.Extensions', '/org/gnome/Shell/Extensions',
            'org.gnome.Shell.Extensions', 'GetExtensionInfo',
            GLib.Variant('(s)', (UUID,)), GLib.VariantType.new('(a{sv})'),
            Gio.DBusCallFlags.NONE, 3000, None)
        return reply.unpack()[0]
    except GLib.Error as error:
        print(f'Running Shell status unavailable: {error.message}')
        return None


def status(target, settings):
    installed = check_existing(target)
    print(f'Extension: {UUID}\nLocation: {target}\nInstalled: {installed is not None}')
    enabled = UUID in settings.get_strv('enabled-extensions')
    blocked = UUID in settings.get_strv('disabled-extensions')
    print(f'Enabled preference: {enabled}; disabled override: {blocked}')
    print(f'All user extensions disabled: {settings.get_boolean("disable-user-extensions")}')
    if installed:
        print(f'Matches repository: {installed == hashes(SOURCE)}')
    info = shell_info()
    if info:
        states = {1: 'ACTIVE', 2: 'INACTIVE', 3: 'ERROR', 4: 'OUT_OF_DATE',
                  5: 'DOWNLOADING', 6: 'INITIALIZED', 7: 'DEACTIVATING', 8: 'ACTIVATING', 99: 'UNINSTALLED'}
        print(f'Running Shell: {states.get(info.get("state"), info.get("state"))}')
        if info.get('error'):
            print(f'Shell error: {info["error"]}')
        if installed and info.get('version') != json.loads((target / 'metadata.json').read_text())['version']:
            print('RELOGIN REQUIRED: running Shell has a different extension version.')
    elif info == {} and installed and enabled and not blocked:
        print('RELOGIN REQUIRED: extension is installed; this Shell has not loaded it yet.')
    elif info is None:
        print('Could not determine runtime activation; installation alone does not confirm it.')


def install(target, state, settings, dry_run):
    version = subprocess.check_output(['gnome-shell', '--version'], text=True).strip()
    if not re.search(r'\b50(?:\.|\b)', version):
        raise ValueError(f'Only GNOME 50 is supported; found {version}')
    if settings.get_boolean('disable-user-extensions'):
        raise ValueError('User extensions are disabled globally; enable them in Extensions first')
    if not settings.get_boolean('allow-extension-installation'):
        raise ValueError('Extension installation is disabled by system policy')
    if any(not settings.is_writable(key) for key in ('enabled-extensions', 'disabled-extensions')):
        raise ValueError('GNOME extension preferences are locked by system policy')
    desired, existing = hashes(SOURCE), check_existing(target)
    metadata = json.loads((SOURCE / 'metadata.json').read_text())
    if metadata['uuid'] != UUID or metadata['shell-version'] != ['50']:
        raise ValueError('Unexpected source extension metadata')
    if existing is not None and existing != desired:
        previous = json.loads((target / 'metadata.json').read_text())
        if metadata['version'] <= previous['version']:
            raise ValueError('Changed extension code requires a higher metadata version; no silent downgrade')
    print(f'{version}: install {UUID} version {metadata["version"]} at {target}')
    if dry_run:
        print('DRY RUN: no files or GNOME preferences changed.')
        return
    changed = existing != desired
    if changed:
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.direct-unlock-', dir=target.parent))
        backup = None
        try:
            for name in FILES:
                shutil.copyfile(SOURCE / name, stage / name)
                (stage / name).chmod(0o644)
            (stage / MANIFEST).write_text(json.dumps({'uuid': UUID, 'files': desired}, indent=2) + '\n')
            stage.chmod(0o755)
            if existing is not None:
                state.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup = Path(tempfile.mkdtemp(prefix='backup-', dir=state)) / UUID
                shutil.copytree(target, backup)
                # Keep the replacement rename on the same filesystem as the target.
                old = stage.with_name(stage.name + '-previous')
                target.rename(old)
            try:
                stage.rename(target)
                configure(settings, True)
            except BaseException:
                if target.exists():
                    shutil.rmtree(target)
                if existing is not None:
                    old.rename(target)
                raise
            if existing is not None:
                shutil.rmtree(old)
                print(f'Previous extension backed up at {backup}')
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    else:
        configure(settings, True)
        print('Extension files already match; enabled preference saved.')
    if changed:
        print('RELOGIN REQUIRED: save work and log out/in to load the new code. No session restart performed.')
    status(target, settings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'status', 'disable'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as the desktop user, without sudo')
    try:
        settings = Gio.Settings.new('org.gnome.shell')
        target, state = paths()
        if args.action == 'install':
            install(target, state, settings, args.dry_run)
        elif args.action == 'disable':
            if args.dry_run:
                print(f'DRY RUN: would disable only {UUID}; no files or preferences changed.')
            else:
                configure(settings, False)
                print('Extension disabled. Files retained for reinstall; other extensions unchanged.')
        else:
            status(target, settings)
    except (ValueError, OSError, KeyError, GLib.Error, subprocess.SubprocessError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
