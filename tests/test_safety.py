"""Exercise installer failure paths without changing packages or services."""
import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import common
import manage
import build


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = common.REPO / 'artifacts/drag'
        self.m = common.load_artifact(self.artifacts, 'drag')
        self.paths = (self.root / 'libraries', self.root / 'config/override.conf', self.root / 'state')
        self.args = argparse.Namespace(component='drag', service=manage.SERVICE, dry_run=False)

    def test_path_escape_and_corrupt_artifact_rejected(self):
        outside = self.root / 'outside'
        outside.write_text('private')
        folder = self.root / 'artifacts'
        folder.mkdir()
        (folder / 'escape').symlink_to(outside)
        for name in ('../outside', str(outside), 'escape'):
            with self.assertRaises(ValueError):
                common.safe_path(folder, name)
        (folder / 'library.so').write_bytes(b'corrupted')
        (folder / 'manifest.json').write_text(json.dumps({
            'schema': 1, 'component': 'drag', 'files': {'library.so': '0' * 64}}))
        with self.assertRaisesRegex(ValueError, 'Checksum'):
            common.load_artifact(folder, 'drag')

    def test_arch_and_release_mismatch_rejected(self):
        for key, value in [('architecture', 'arm64'), ('release', '28.04'), ('distro', 'debian')]:
            current = {k: self.m[k] for k in ('architecture', 'release', 'distro')}
            current[key] = value
            with self.assertRaises(ValueError):
                common.compatible(self.m, current)

    def test_atomic_replace_preserves_already_open_library(self):
        p = self.root / 'library.so'
        p.write_bytes(b'old-mapped-library')
        with p.open('rb') as old:
            common.atomic_write(p, b'new-library')
            self.assertEqual(old.read(), b'old-mapped-library')
        self.assertEqual(p.read_bytes(), b'new-library')

    def test_unknown_override_is_preserved(self):
        p = self.paths[1]
        p.parent.mkdir()
        p.write_text('[Service]\nEnvironment="LD_PRELOAD=/different/library.so"\n')
        before = p.read_bytes()
        with self.assertRaises(ValueError):
            manage.managed_config(p, 'drag', {}, 'replacement')
        self.assertEqual(p.read_bytes(), before)

    def drag_context(self):
        from contextlib import ExitStack
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(manage, 'user_paths', return_value=self.paths))
        stack.enter_context(patch.object(manage.os, 'geteuid', return_value=1000))
        stack.enter_context(patch.object(manage, 'package_version', return_value=self.m['base_version']))
        stack.enter_context(patch.object(manage, 'output', return_value='loaded'))
        linker = stack.enter_context(patch.object(manage, 'linker_check'))
        commands = stack.enter_context(patch.object(manage, 'run'))
        return linker, commands

    def test_dry_run_has_no_writes_or_service_actions(self):
        linker, commands = self.drag_context()
        self.args.dry_run = True
        manage.apply_libraries(self.args, self.m, self.artifacts)
        self.assertEqual(list(self.root.iterdir()), [])
        linker.assert_not_called()
        commands.assert_not_called()

    def test_linker_failure_does_not_publish_override(self):
        linker, commands = self.drag_context()
        linker.side_effect = ValueError('incompatible ABI')
        with self.assertRaises(ValueError):
            manage.apply_libraries(self.args, self.m, self.artifacts)
        self.assertFalse(self.paths[1].exists())
        commands.assert_not_called()

    def test_service_failure_restores_previous_override(self):
        linker, commands = self.drag_context()
        p = self.paths[1]
        p.parent.mkdir()
        original = manage.legacy_configs('drag')[-1]
        p.write_text(original)
        commands.side_effect = OSError('daemon reload failed')
        with patch.object(manage.subprocess, 'run') as recovery:
            with self.assertRaises(OSError):
                manage.apply_libraries(self.args, self.m, self.artifacts)
            recovery.assert_called_once()
        self.assertEqual(p.read_text(), original)

    def test_apply_reapply_disable_in_another_home(self):
        linker, commands = self.drag_context()
        manage.apply_libraries(self.args, self.m, self.artifacts)
        p = self.paths[1]
        before = p.read_text()
        self.assertIn(str(self.paths[0]), before)
        self.assertNotIn('/home/testors', before)
        manage.apply_libraries(self.args, self.m, self.artifacts)
        self.assertEqual(p.read_text(), before)
        state = manage.state_read(self.paths[2])
        folder = Path(state['directory'])
        self.assertEqual(common.digest(folder / self.m['soname']), self.m['files'][self.m['library']])
        manage.disable_libraries(self.args, self.m)
        self.assertFalse(p.exists())
        self.assertTrue((folder / self.m['library']).exists())

    def test_newer_mutter_cannot_be_downgraded_by_install_or_rollback(self):
        args = argparse.Namespace(dry_run=True)
        folder = common.REPO / 'artifacts/mutter'
        m = common.load_artifact(folder, 'mutter')
        with patch.object(manage, 'check_mutter_metadata'), \
             patch.object(manage, 'package_version', return_value='50.2-0ubuntu1'), \
             patch.object(manage, 'state_read', return_value={}), \
             patch.object(manage, 'apt_install') as apt:
            with self.assertRaises(ValueError):
                manage.install_mutter(args, m, folder)
            with self.assertRaises(ValueError):
                manage.rollback_mutter(args, m, folder)
            apt.assert_not_called()

    def test_updated_libinput_requires_a_matching_rebuild(self):
        self.drag_context()
        with patch.object(manage, 'package_version', return_value='1.31.2-1ubuntu1'):
            with self.assertRaises(ValueError):
                manage.apply_libraries(self.args, self.m, self.artifacts)
        self.assertFalse(self.paths[1].exists())

    def test_patch_distinguishes_already_fixed_and_conflicting_sources(self):
        p = self.root / 'change.patch'
        p.write_text('--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new\n')
        f = self.root / 'file'
        for text, expected in [('old\n', 'applicable'), ('new\n', 'already-applied'), ('different\n', 'conflict')]:
            f.write_text(text)
            self.assertEqual(build.patch_state(self.root, p), expected)
            self.assertEqual(f.read_text(), text)


if __name__ == '__main__':
    unittest.main()
