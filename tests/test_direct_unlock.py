"""Installer tests use a temporary home and in-memory preferences only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import direct_unlock as du


class Settings:
    def __init__(self):
        self.values = {'enabled-extensions': ['existing@example'], 'disabled-extensions': ['off@example']}
        self.fail_once = None

    def get_strv(self, key):
        return list(self.values[key])

    def set_strv(self, key, value):
        if key == self.fail_once:
            self.fail_once = None
            return False
        self.values[key] = list(value)
        return True

    def get_boolean(self, key):
        return key == 'allow-extension-installation'

    def is_writable(self, key):
        return True


class DirectUnlockTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.target = self.root / 'data/extensions' / du.UUID
        self.state = self.root / 'state'
        self.settings = Settings()
        for target, value in [('subprocess.check_output', 'GNOME Shell 50.1'), ('shell_info', {})]:
            p = patch(f'direct_unlock.{target}', return_value=value)
            p.start()
            self.addCleanup(p.stop)
        p = patch('direct_unlock.Gio.Settings.sync')
        p.start()
        self.addCleanup(p.stop)
        sink = contextlib.redirect_stdout(io.StringIO())
        sink.__enter__()
        self.addCleanup(sink.__exit__, None, None, None)

    def install(self, dry_run=False):
        du.install(self.target, self.state, self.settings, dry_run)

    def test_install_repeat_disable_preserves_other_extensions(self):
        self.install()
        self.install()
        self.assertEqual(du.check_existing(self.target), du.hashes(du.SOURCE))
        self.assertEqual(self.settings.values['enabled-extensions'], ['existing@example', du.UUID])
        du.configure(self.settings, False)
        self.assertEqual(self.settings.values['enabled-extensions'], ['existing@example'])
        self.assertEqual(self.settings.values['disabled-extensions'], ['off@example', du.UUID])

    def test_dry_run_does_not_create_files_or_change_settings(self):
        self.install(dry_run=True)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.settings.values['enabled-extensions'], ['existing@example'])

    def test_policy_failure_restores_preferences_and_files(self):
        self.settings.fail_once = 'disabled-extensions'
        self.settings.values['disabled-extensions'].append(du.UUID)
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse(self.target.exists())
        self.assertEqual(self.settings.values['enabled-extensions'], ['existing@example'])
        self.assertIn(du.UUID, self.settings.values['disabled-extensions'])

    def test_unknown_or_edited_installation_is_preserved(self):
        self.target.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.install()
        self.target.rmdir()
        self.install()
        edited = self.target / 'extension.js'
        edited.write_text('personal edit')
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(edited.read_text(), 'personal edit')

    def test_symlink_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.root / 'elsewhere')
        with self.assertRaises(ValueError):
            self.install()
        self.assertTrue(self.target.is_symlink())

    def test_upgrade_backup_and_failed_upgrade_restore(self):
        self.install()
        source = self.root / 'source'
        du.shutil.copytree(du.SOURCE, source)
        metadata = json.loads((source / 'metadata.json').read_text())
        metadata['version'] += 1
        (source / 'metadata.json').write_text(json.dumps(metadata))
        with patch.object(du, 'SOURCE', source):
            self.settings.values['disabled-extensions'].append(du.UUID)
            self.settings.fail_once = 'disabled-extensions'
            with self.assertRaises(ValueError):
                self.install()
            self.assertEqual(du.hashes(self.target), du.hashes(Path(__file__).resolve().parents[1] / 'extensions' / du.UUID))
            self.install()
            self.assertEqual(du.hashes(self.target), du.hashes(source))
            self.assertTrue(list(self.state.glob('backup-*/*/metadata.json')))


if __name__ == '__main__':
    unittest.main()
