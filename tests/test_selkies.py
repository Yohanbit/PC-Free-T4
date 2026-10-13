"""Offline unit/integration checks. No install, network, Colab or live processes."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pcfree_selkies_test', ROOT / 'scripts/selkies-desktop.py')
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)


class SelkiesTests(unittest.TestCase):
    def test_import_and_embedded_syntax(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            ast.parse(path.read_text(), filename=str(path))
        for filename in ('PC-Free-T4.ipynb', 'PC-Free-T4-Rapido.ipynb'):
            document = json.loads((ROOT / filename).read_text())
            self.assertEqual(document['nbformat'], 4)
            self.assertEqual(document['metadata']['accelerator'], 'GPU')
            for cell in document['cells']:
                if cell['cell_type'] == 'code':
                    self.assertEqual(cell['outputs'], [])
                    self.assertIsNone(cell['execution_count'])
                    ast.parse(''.join(cell['source']))
            tree = ast.parse(''.join(document['cells'][1]['source']))
            sources = ast.literal_eval(tree.body[0].value)
            for name, source in sources.items():
                path = ROOT / 'scripts' / name
                if path.exists():
                    self.assertEqual(source, path.read_text(), name + ' stale: regenerate notebooks')
            self.assertIn('selkies-desktop.py', sources)
            self.assertNotIn('07-rustdesk.py', sources)

    def test_run_all_schedule_and_no_apps(self):
        for filename in ('PC-Free-T4.ipynb', 'PC-Free-T4-Rapido.ipynb'):
            document = json.loads((ROOT / filename).read_text())
            env = {}
            exec(''.join(document['cells'][1]['source']), env)
            calls = []
            env['_core']['bootstrap'] = lambda **kwargs: calls.append(kwargs) or {'env': {}}
            background = []
            env['optional_module'] = lambda name: {'roblox_background': lambda session: background.append(session)}
            for cell in document['cells'][2:]:
                if cell['cell_type'] == 'code':
                    exec(''.join(cell['source']), env)
            self.assertEqual(calls, [{'firefox': True, 'framerate': 60, 'bitrate': 5000}])
            self.assertEqual(len(background), 1)
            for key, value in env.items():
                if key.startswith('INSTALL_') or key in ('EXPORT_WORLDS', 'RESTORE_WORLDS', 'STEAM_GAMEPADS'):
                    self.assertIs(value, key == 'INSTALL_ROBLOX', key)

    def test_private_web_client_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream'
            source.mkdir()
            (source / 'assets').mkdir()
            original = '<html><head></head><body>Selkies</body></html>'
            (source / 'index.html').write_text(original)
            with patch.object(CORE, 'BASE', Path(folder) / 'state'):
                destination = Path(CORE.prepare_web_client(source))
                self.assertEqual((source / 'index.html').read_text(), original)
                self.assertIn('pcfree-input-guard.js', (destination / 'index.html').read_text())
                self.assertEqual((destination / 'pcfree-input-guard.js').read_text(), CORE.INPUT_GUARD_JS)
                CORE.prepare_web_client(source)
                self.assertEqual((destination / 'index.html').read_text().count('pcfree-input-guard.js'), 1)
                self.assertNotIn('stopPropagation', CORE.INPUT_GUARD_JS)
                self.assertNotIn('pointerdown', CORE.INPUT_GUARD_JS)

    def test_version_exact_and_official_origin(self):
        data = 'lib | 580.82.09-0ubuntu1 | https://archive.ubuntu.com\nlib | 1:580.82.07-0ubuntu2 | https://archive.ubuntu.com'
        self.assertEqual(CORE.matching_version(data, '580.82.07'), '1:580.82.07-0ubuntu2')
        with self.assertRaisesRegex(RuntimeError, 'exactas'):
            CORE.matching_version(data, '580.99.00')
        self.assertTrue(CORE.official_ubuntu_uri('http://us.archive.ubuntu.com/ubuntu/pool/pkg.deb'))
        self.assertFalse(CORE.official_ubuntu_uri('https://archive.ubuntu.com.evil.example/pkg.deb'))
        self.assertFalse(CORE.official_ubuntu_uri('https://developer.download.nvidia.com/pkg.deb'))
        prefix = 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/'
        self.assertTrue(CORE.official_ubuntu_uri(prefix + 'libnvidia-gl-580_580.82.07-0ubuntu1_amd64.deb'))
        self.assertTrue(CORE.official_ubuntu_uri(prefix + './libnvidia-gl-580_580.82.07-0ubuntu1_amd64.deb'))
        for uri in (prefix.replace('https:', 'http:'),
                    prefix.replace('ubuntu2404', 'ubuntu2204'),
                    prefix.replace('x86_64', 'arm64'),
                    prefix.replace('nvidia.com/', 'nvidia.com.evil.example/'),
                    prefix + '../pkg.deb', prefix + '%2e%2e/pkg.deb',
                    prefix.replace('https://', 'https://user:password@')):
            self.assertFalse(CORE.official_ubuntu_uri(uri), uri)

    def test_optional_installer_dispatch(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text())
        calls = []
        env = {'SESSION': {'env': {}}, '_sober_task': None,
               'optional_module': lambda name: {
                   'install_steam': lambda session: calls.append(('steam', session)),
                   'install_gamepads': lambda session: calls.append(('gamepads', session)),
                   'install_app': lambda option, session: calls.append((option, session))}}
        env['_apps'] = env['optional_module']('compat-apps.py')
        for cell in document['cells']:
            source = ''.join(cell['source'])
            if cell['cell_type'] != 'code' or not source.startswith('# @title'):
                continue
            for toggle in ('INSTALL_GAMEPADS', 'INSTALL_BLENDER', 'INSTALL_GODOT', 'INSTALL_VINEGAR'):
                source = source.replace(toggle + ' = False', toggle + ' = True')
            if 'INSTALL_GAMEPADS =' in source or 'INSTALL_BLENDER =' in source:
                exec(source, env)
        self.assertEqual([call[0] for call in calls], ['gamepads', 'blender', 'godot', 'vinegar'])
        notes = '\n'.join(''.join(cell['source']) for cell in document['cells'] if cell['cell_type'] == 'markdown')
        self.assertIn('SSE4.1', notes)
        self.assertNotIn('namespaces bloqueados en esta VM', notes)

    def test_apt_rejects_kernel_driver_changes(self):
        for output in ('Inst nvidia-driver-580 (version)\n', 'Inst linux-modules-foo (version)\n', 'Remv something\n'):
            with patch.object(CORE, 'capture', return_value=output), patch.object(CORE, 'logged') as run:
                with self.assertRaises(RuntimeError):
                    CORE.safe_apt_install(['test'])
                run.assert_not_called()
        with patch.object(CORE, 'capture', side_effect=['Inst harmless (version)',
                 "'https://untrusted.example/harmless.deb' harmless.deb 123 SHA256:abc"]), \
             patch.object(CORE, 'logged') as run:
            with self.assertRaisesRegex(RuntimeError, 'origen'):
                CORE.safe_apt_install(['harmless'])
            run.assert_not_called()

    def test_vulkan_icd_isolated_absolute_path(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / 'nvidia/root'
            library = root / 'usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0'
            library.parent.mkdir(parents=True)
            library.write_text('unit-test-placeholder')
            source = root / 'usr/share/vulkan/icd.d/nvidia_icd.json'
            source.parent.mkdir(parents=True)
            original = {'file_format_version': '1.0.0', 'ICD': {
                'library_path': 'libGLX_nvidia.so.0', 'api_version': '1.3.0'}}
            source.write_text(json.dumps(original))
            with patch.object(CORE, 'BASE', base):
                result = Path(CORE.vulkan_icd(root))
            document = json.loads(result.read_text())
            self.assertEqual(document['ICD']['library_path'], str(library))
            self.assertEqual(document['ICD']['api_version'], '1.3.0')
            self.assertEqual(json.loads(source.read_text()), original)
            self.assertEqual(result.stat().st_mode & 0o777, 0o644)
            library.unlink()
            with patch.object(CORE, 'BASE', base), self.assertRaisesRegex(RuntimeError, 'incompletos'):
                CORE.vulkan_icd(root)

    def test_apt_only_explicit_validated_local_deb(self):
        metadata = 'Package: selkies\nVersion: 2.0.0-1~ubuntu24.04\nArchitecture: amd64\n'
        self.assertEqual(CORE.SELKIES_DEB_VERSION, '2.0.0-1~ubuntu24.04')
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            deb = base / 'selkies.deb'
            deb.write_bytes(b'offline placeholder')
            entries = [(f"'file:{deb}' selkies_2.0.0-1~ubuntu24.04_amd64.deb 123", True),
                       ("'' selkies_2.0.0-1~ubuntu24.04_amd64.deb 123", True),
                       ("'' selkies_2.0.0_amd64.deb 123", False),
                       ("'' another_1.0_amd64.deb 123", False),
                       ("'file:/tmp/untrusted.deb' selkies_2.0.0-1~ubuntu24.04_amd64.deb 123", False),
                       (f"'file://untrusted{deb}' selkies_2.0.0-1~ubuntu24.04_amd64.deb 123", False)]
            for output, allowed in entries:
                with patch.object(CORE, 'BASE', base), \
                     patch.object(CORE, 'capture', side_effect=[metadata, 'Inst selkies (2.0.0-1~ubuntu24.04)', output]), \
                     patch.object(CORE, 'logged') as run:
                    if allowed:
                        CORE.safe_apt_install([str(deb)], validated_local_deb=deb)
                        run.assert_called_once()
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'origen'):
                            CORE.safe_apt_install([str(deb)], validated_local_deb=deb)
                        run.assert_not_called()
            with patch.object(CORE, 'capture', side_effect=['Inst selkies (2.0.0-1~ubuntu24.04)', entries[0][0]]), \
                 patch.object(CORE, 'logged') as run:
                with self.assertRaisesRegex(RuntimeError, 'origen'):
                    CORE.safe_apt_install([str(deb)])
                run.assert_not_called()
            for wrong_version in ('2.0.0', '2.0.0-2~ubuntu24.04', '99.0'):
                with patch.object(CORE, 'BASE', base), \
                     patch.object(CORE, 'capture', return_value=metadata.replace(CORE.SELKIES_DEB_VERSION, wrong_version)):
                    with self.assertRaisesRegex(RuntimeError, 'Identidad'):
                        CORE.safe_apt_install([str(deb)], validated_local_deb=deb)

    def test_persistent_desktop_bus(self):
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertIn("env['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={runtime}/bus'", source)
        self.assertIn("spawn(['dbus-daemon', '--session', '--nofork'", source)
        self.assertIn("wait_for(bus_ready, 'D-Bus de escritorio', [dbus])", source)
        self.assertNotIn("spawn(['dbus-run-session'", source)

    def test_private_state_and_idempotency(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            session = {'env': {}, 'processes': {'xorg': {'pid': 123, 'start': '42'}}}
            CORE.private_json(base / 'session.json', session)
            CORE.private_json(base / 'access.json', {'username': 'pcfree', 'password': 'fictional-unit-test', 'url': 'test'})
            self.assertEqual((base / 'access.json').stat().st_mode & 0o777, 0o600)
            self.assertNotIn('password', (base / 'session.json').read_text())
            with patch.object(CORE, 'BASE', base), patch.object(CORE, 'pid_identity', return_value='42'), \
                 patch.object(CORE, 'preflight') as preflight, patch.object(CORE, 'show_access') as access:
                self.assertEqual(CORE.bootstrap(), session)
                preflight.assert_not_called()
                access.assert_called_once()
            with patch.object(CORE, 'BASE', base), patch.object(CORE, 'pid_identity', return_value='43'), \
                 patch.object(CORE, 'preflight') as preflight:
                with self.assertRaisesRegex(RuntimeError, 'previo'):
                    CORE.bootstrap()
                preflight.assert_not_called()

    def test_launcher_argv_and_no_shell(self):
        session = {'user': 'pcfree-browser', 'env': {'DISPLAY': ':98', 'LD_LIBRARY_PATH': '/isolated'}}
        source = CORE.launcher_source(session)
        ast.parse(source)
        self.assertIn("os.execvpe(sys.argv[1], sys.argv[1:], env)", source)
        self.assertIn("'/usr/$LIB/selkies_input_interposer.so'", source)
        self.assertNotIn('shell=True', source)
        self.assertIn('os.setuid(account.pw_uid)', source)

    def test_launcher_fake_udev_and_argv_runtime(self):
        session = {'user': 'pcfree-browser', 'env': {'DISPLAY': ':98', 'LD_LIBRARY_PATH': '/isolated'}}
        account = types.SimpleNamespace(pw_name='pcfree-browser', pw_uid=1001, pw_gid=1001)
        args = ['pcfree-run', '/path/game', 'space arg', '$(touch /never-create)', '--flag']
        for fake_available in (False, True):
            def exists(path):
                return path.startswith('/usr/lib/') or fake_available
            inherited = {'SDL_JOYSTICK_DISABLE_UDEV': '1', 'SDL_JOYSTICK_DEVICE': 'stale',
                         'LD_PRELOAD': '/unwanted', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/desktop-bus'}
            with patch('pwd.getpwnam', return_value=account), patch('os.geteuid', return_value=1001), \
                 patch('os.path.exists', side_effect=exists), patch('os.execvpe') as execute, \
                 patch('sys.argv', args), patch.dict(os.environ, inherited, clear=True):
                exec(CORE.launcher_source(session), {})
                program, passed, env = execute.call_args.args
            self.assertEqual(program, args[1])
            self.assertEqual(passed, args[1:])
            self.assertEqual(env['DBUS_SESSION_BUS_ADDRESS'], 'unix:path=/desktop-bus')
            self.assertNotIn('/unwanted', env['LD_PRELOAD'])
            if fake_available:
                self.assertIn('/tmp/pcfree-selkies/fake-udev/$LIB/libudev.so.1', env['LD_PRELOAD'])
                self.assertNotIn('SDL_JOYSTICK_DEVICE', env)
                self.assertNotIn('SDL_JOYSTICK_DISABLE_UDEV', env)
            else:
                self.assertEqual(env['SDL_JOYSTICK_DISABLE_UDEV'], '1')
                self.assertIn('/dev/input/event1000', env['SDL_JOYSTICK_DEVICE'])

    def test_security_static(self):
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertIn('--addr=127.0.0.1', source)
        self.assertIn('--enable-basic-auth=true', source)
        self.assertIn("'--protocol', 'http2'", source)
        self.assertIn("server_env.pop('LD_PRELOAD', None)", source)
        self.assertIn("server_env['LD_PRELOAD'] = shm_perms", source)
        self.assertIn('shm_perms = shm_perms_library()', source)
        self.assertIn("'--backpressure-queue-size=2'", source)
        self.assertIn("'--encoder=h264enc'", source)
        self.assertNotIn("'-ac'", source)
        self.assertNotIn('xhost', source)
        self.assertNotIn('time.sleep(7)', source)
        self.assertIn("python.symlink_to('/usr/bin/python3.12')", source)
        self.assertNotIn("Path('/usr/bin/python3')", source)

    def test_generated_helper_syntax(self):
        # Capture filesystem writes, not real /usr/local or sudoers changes.
        writes = {}
        def write_text(path, text, **kwargs):
            writes[str(path)] = text
        with patch.object(Path, 'write_text', write_text), patch.object(Path, 'chmod'), \
             patch.object(CORE, 'logged'), patch.object(CORE, 'shortcut'):
            CORE.package_installer({'home': '/fictional'})
        ast.parse(writes['/usr/local/sbin/pcfree-install-package'])
        helper_tree = ast.parse(writes['/usr/local/sbin/pcfree-install-package'])
        validator = next(node for node in helper_tree.body if isinstance(node, ast.FunctionDef))
        namespace = {'urllib': __import__('urllib')}
        exec(compile(ast.Module(body=[validator], type_ignores=[]), '<validator>', 'exec'), namespace)
        for uri in ('https://archive.ubuntu.com/ubuntu/pkg.deb',
                    'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/pkg.deb',
                    'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/./pkg.deb',
                    'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/../pkg.deb',
                    'https://developer.download.nvidia.com/elsewhere/pkg.deb',
                    'https://evil.example/pkg.deb'):
            self.assertEqual(namespace['official_ubuntu_uri'](uri), CORE.official_ubuntu_uri(uri))
        self.assertIn('ALLOWED', writes['/usr/local/sbin/pcfree-install-package'])
        self.assertNotIn('NOPASSWD: ALL', writes['/etc/sudoers.d/pcfree-packages'])

    def test_builder_deterministic_and_preserves_backup(self):
        targets = [ROOT / name for name in ('PC-Free-T4.ipynb', 'PC-Free-T4-Rapido.ipynb', 'Drive-Backups.ipynb')]
        before = [path.read_bytes() for path in targets]
        subprocess.run(['python', str(ROOT / 'tools/build-notebooks.py')], check=True)
        self.assertEqual(before, [path.read_bytes() for path in targets])


if __name__ == '__main__':
    unittest.main(verbosity=2)
