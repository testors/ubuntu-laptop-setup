import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import admin_fingerprint as auth


class AdminFingerprintTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.pam = self.root / 'pam.d'
        self.pam.mkdir()
        self.original = b'#%PAM-1.0\nsession required pam_limits.so\n@include common-auth\n@include common-account\n'
        for name in ('sudo', 'sudo-i'):
            (self.pam / name).write_bytes(self.original)
        (self.pam / 'common-auth').write_text('auth required pam_unix.so\n')
        vendor = self.root / 'polkit-vendor'
        vendor.write_text('@include common-auth\n@include common-account\n')
        for key, value in [('PAM', self.pam), ('VENDOR', vendor), ('STATE', self.root / 'state')]:
            mock = patch.object(auth, key, value)
            mock.start()
            self.addCleanup(mock.stop)
        self.args = argparse.Namespace(dry_run=False, user='example', backup=None)

    def test_plan_keeps_password_account_and_session_policies(self):
        before, after, modes = auth.plan()
        for name in ('sudo', 'sudo-i'):
            self.assertEqual(after[name].replace(auth.BLOCK.encode(), b''), before[name])
            self.assertLess(after[name].index(auth.RULE.encode()), after[name].index(b'@include common-auth'))
        self.assertIsNone(before['polkit-1'])
        for kind in ('auth', 'account', 'password', 'session'):
            self.assertIn(f'{kind} include {auth.VENDOR}\n'.encode(), after['polkit-1'])

    def test_dry_run_does_not_create_backups_or_policies(self):
        self.args.dry_run = True
        auth.install(self.args)
        self.assertFalse(auth.STATE.exists())
        self.assertFalse((self.pam / 'polkit-1').exists())
        self.assertEqual((self.pam / 'sudo').read_bytes(), self.original)

    def test_unknown_polkit_or_extra_auth_rule_rejected(self):
        (self.pam / 'polkit-1').write_text('auth required pam_custom.so\n')
        with self.assertRaises(ValueError):
            auth.plan()
        (self.pam / 'polkit-1').unlink()
        (self.pam / 'sudo').write_bytes(b'auth required pam_custom.so\n' + self.original)
        with self.assertRaises(ValueError):
            auth.plan()
        (self.pam / 'sudo').write_bytes(self.original + b'@include custom-mfa\n')
        with self.assertRaises(ValueError):
            auth.plan()

    def test_account_check_failure_restores_every_original(self):
        with patch.object(auth, 'account_checks', side_effect=ValueError('account failure')):
            with self.assertRaises(ValueError):
                auth.install(self.args)
        for name in ('sudo', 'sudo-i'):
            self.assertEqual((self.pam / name).read_bytes(), self.original)
        self.assertFalse((self.pam / 'polkit-1').exists())
        self.assertFalse((auth.STATE / 'state.json').exists())

    def test_install_idempotent_and_rollback_preserves_later_changes(self):
        with patch.object(auth, 'account_checks'):
            auth.install(self.args)
            state = (auth.STATE / 'state.json').read_bytes()
            auth.install(self.args)
            self.assertEqual((auth.STATE / 'state.json').read_bytes(), state)
        path = self.pam / 'sudo-i'
        installed = path.read_bytes()
        path.write_bytes(installed + b'# later administrator change\n')
        with self.assertRaises(ValueError):
            auth.rollback(self.args)
        self.assertTrue((self.pam / 'polkit-1').exists())
        path.write_bytes(installed)
        auth.rollback(self.args)
        self.assertFalse((self.pam / 'polkit-1').exists())
        self.assertEqual((self.pam / 'sudo').read_bytes(), self.original)


if __name__ == '__main__':
    unittest.main()
