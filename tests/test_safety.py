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

    def test_catalog_selects_matching_drag_base_version(self):
        catalog = common.load_artifact_catalog('drag')
        bases = {m['base_version'] for _, m in catalog}
        self.assertIn('1.31.1-1ubuntu1.2', bases)
        self.assertIn('1.31.1-1ubuntu1', bases)
        selected = common.select_drag_artifact(catalog, '1.31.1-1ubuntu1')
        self.assertIsNotNone(selected)
        self.assertEqual(selected[1]['base_version'], '1.31.1-1ubuntu1')
        self.assertIsNone(common.select_drag_artifact(catalog, '9.9.9-1'))

    def test_resolve_drag_uses_catalog_without_rebuild(self):
        with patch.object(manage, 'package_version', return_value='1.31.1-1ubuntu1'):
            path, m = manage.resolve_artifacts('drag', rebuild=False)
        self.assertEqual(m['base_version'], '1.31.1-1ubuntu1')
        self.assertTrue((path / 'manifest.json').is_file())

    def test_resolve_drag_dry_run_reports_rebuild_without_building(self):
        with patch.object(manage, 'package_version', return_value='9.9.9-1ubuntu1'), \
             patch.object(manage, 'load_artifact_catalog', return_value=[]), \
             patch.object(manage, 'check_rebuild_host'), \
             patch('build.rebuild_component') as rebuild:
            path, m = manage.resolve_artifacts('drag', rebuild=True, dry_run=True)
            rebuild.assert_not_called()
            self.assertIsNone(path)
            self.assertIsNone(m)

    def test_mutter_catalog_prefers_matching_base_and_never_downgrades(self):
        archive = (self.root / 'mutter', {
            'base_version': '50.1-0ubuntu2.4', 'version': '50.1-0ubuntu2.4+keymapfix1'})
        catalog = [archive]
        self.assertEqual(common.select_mutter_artifact(catalog, archive[1]['base_version']), archive)
        self.assertEqual(common.select_mutter_artifact(catalog, archive[1]['version']), archive)
        self.assertEqual(common.select_mutter_artifact(catalog, '50.1-0ubuntu2.3'), archive)
        self.assertIsNone(common.select_mutter_artifact(catalog, '50.1-0ubuntu2.5'))
        self.assertIsNone(common.select_mutter_artifact(catalog, '50.1-0ubuntu2.3+custom1'))
        another = (self.root / 'newer', {
            'base_version': '50.1-0ubuntu2.5', 'version': '50.1-0ubuntu2.5+keymapfix1'})
        self.assertIsNone(common.select_mutter_artifact([archive, another], '50.1-0ubuntu2.3'))

    def test_mutter_unknown_local_suffix_is_not_replaced_automatically(self):
        with patch.object(manage, 'package_version', return_value='50.1-0ubuntu2.5+custom1'), \
             patch.object(manage, 'load_artifact_catalog', return_value=[]), \
             patch.object(build, 'rebuild_component') as rebuild:
            with self.assertRaisesRegex(ValueError, 'unrecognized local suffix'):
                manage.resolve_artifacts('mutter')
            rebuild.assert_not_called()

    def test_mutter_rebuild_uses_official_base_of_prior_local_patch(self):
        current = '50.1-0ubuntu2.5+keymapfix1'
        with patch.object(manage, 'package_version', return_value=current), \
             patch.object(manage, 'load_artifact_catalog', return_value=[]), \
             patch.object(build, 'rebuild_component', return_value=(self.root, {'base_version': '50.1-0ubuntu2.5'})) as rebuild:
            folder, manifest = manage.resolve_artifacts('mutter')
            self.assertEqual(folder, self.root)
            self.assertEqual(manifest['base_version'], '50.1-0ubuntu2.5')
            rebuild.assert_called_once_with('mutter', '50.1-0ubuntu2.5')

    def test_auto_rebuild_downloads_outside_empty_workdir_and_reuses_result(self):
        base = '9.9.9-1ubuntu1'
        work = self.root / 'build' / f'drag-auto-{base}'
        cache = self.root / 'build' / 'source-cache' / 'drag' / base
        manifest = {'component': 'drag', 'base_version': base}

        def fetch(package, version, dest):
            self.assertEqual((package, version, dest), ('libinput', base, cache))
            self.assertFalse(work.exists())
            dest.mkdir(parents=True)
            dsc = dest / 'libinput.dsc'
            dsc.write_text('source')
            return dsc

        def prepare(args, dest):
            self.assertEqual(dest, work)
            self.assertFalse(work.exists())
            self.assertEqual(args.dsc.parent, cache)
            work.mkdir()
            (work / 'prepared.json').write_text(json.dumps(manifest))
            return manifest

        def build_library(args, dest, meta):
            self.assertEqual((dest, meta), (work, manifest))
            (dest / 'artifacts').mkdir()
            (dest / 'artifacts/manifest.json').write_text('{}')

        with patch.object(build, 'REPO', self.root), \
             patch.object(build, 'check_rebuild_host'), \
             patch.object(build.os, 'geteuid', return_value=1000), \
             patch.object(build, 'missing_build_tools', return_value=[]) as missing, \
             patch.object(build, 'fetch_ubuntu_source', side_effect=fetch) as fetched, \
             patch.object(build, 'prepare', side_effect=prepare) as prepared, \
             patch.object(build, 'build_library', side_effect=build_library) as built, \
             patch.object(build, 'load_artifact', return_value=manifest):
            self.assertEqual(build.rebuild_component('drag', base), (work / 'artifacts', manifest))
            self.assertEqual(build.rebuild_component('drag', base), (work / 'artifacts', manifest))
            missing.assert_called_once()
            fetched.assert_called_once()
            prepared.assert_called_once()
            built.assert_called_once()

    def test_auto_rebuild_refuses_root_before_fetch(self):
        with patch.object(build, 'REPO', self.root), \
             patch.object(build, 'check_rebuild_host'), \
             patch.object(build.os, 'geteuid', return_value=0), \
             patch.object(build, 'fetch_ubuntu_source') as fetch:
            with self.assertRaisesRegex(ValueError, 'regular user'):
                build.rebuild_component('drag', '9.9.9-1ubuntu1')
            fetch.assert_not_called()

    def test_mutter_rollback_uses_saved_version_and_rejects_escaped_path(self):
        root_state = self.root / 'state'
        state_dir = root_state / 'mutter'
        saved = state_dir / 'rebuild-version'
        saved.mkdir(parents=True)
        state_file = state_dir / 'state.json'
        state_file.write_text(json.dumps({'directory': str(saved)}))
        manifest = {'component': 'mutter', 'base_version': '50.1-0ubuntu2.5'}
        with patch.object(manage, 'ROOT_STATE', root_state), \
             patch.object(manage, 'load_artifact', return_value=manifest) as loaded, \
             patch.object(manage, 'load_artifact_catalog') as catalog:
            self.assertEqual(manage.resolve_rollback_artifacts(), (saved, manifest))
            loaded.assert_called_once_with(saved, 'mutter')
            catalog.assert_not_called()
            state_file.write_text(json.dumps({'directory': str(self.root)}))
            with self.assertRaisesRegex(ValueError, 'backup path'):
                manage.resolve_rollback_artifacts()

    def test_mutter_rollback_dry_run_elevates_without_overriding_saved_version(self):
        argv = ['ubuntu-custom', 'rollback', 'mutter', '--dry-run']
        with patch.object(sys, 'argv', argv), \
             patch.object(manage.os, 'geteuid', return_value=1000), \
             patch.dict(manage.os.environ, {}, clear=True), \
             patch.object(manage.shutil, 'which', return_value=None), \
             patch.object(manage, 'resolve_rollback_artifacts') as resolve, \
             patch.object(manage.os, 'execvp', side_effect=RuntimeError('escalated')) as execvp:
            with self.assertRaisesRegex(RuntimeError, 'escalated'):
                manage.main()
            resolve.assert_not_called()
            command = execvp.call_args.args[1]
            self.assertIn('--dry-run', command)
            self.assertNotIn('--artifacts', command)
            self.assertEqual(command[0:2], ['sudo', '/usr/bin/python3'])

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
