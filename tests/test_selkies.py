"""Offline unit/integration checks. No install, network, Colab or live processes."""
import ast
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pcfree_selkies_test', ROOT / 'scripts/selkies-desktop.py')
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)


def find_cell(document, needle):
    for index, cell in enumerate(document['cells']):
        if needle in ''.join(cell['source']):
            return index, cell
    raise AssertionError(f'No se encontró la celda: {needle}')


class SelkiesTests(unittest.TestCase):
    def test_import_and_embedded_syntax(self):
        for path in (ROOT / 'scripts').glob('*.py'):
            ast.parse(path.read_text(), filename=str(path))
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        self.assertEqual(document['nbformat'], 4)
        self.assertEqual(document['metadata']['accelerator'], 'GPU')
        for cell in document['cells']:
            if cell['cell_type'] == 'code':
                self.assertEqual(cell['outputs'], [])
                self.assertIsNone(cell['execution_count'])
                if ''.join(cell['source']).strip():
                    ast.parse(''.join(cell['source']))

    def test_notebook_sources_embedded(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        cell2_code = ''.join(document['cells'][2]['source'])
        env = {}
        exec(compile(cell2_code, 'cell2', 'exec'), env)
        sources = env.get('SOURCES', {})
        self.assertIn('selkies-desktop.py', sources)
        for name, source in sources.items():
            path = ROOT / 'scripts' / name
            if path.exists():
                self.assertEqual(source, path.read_text(encoding='utf-8'))

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
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        notes = '\n'.join(''.join(cell['source']) for cell in document['cells'] if cell['cell_type'] == 'markdown')
        self.assertIn('Selkies', notes)

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
        version = CORE.SELKIES_DEB_VERSION
        self.assertEqual(version, '2.1.0-1~ubuntu24.04')
        metadata = f'Package: selkies\nVersion: {version}\nArchitecture: amd64\n'
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            deb = base / 'selkies.deb'
            deb.write_bytes(b'offline placeholder')
            filename = f'selkies_{version}_amd64.deb'
            entries = [(f"'file:{deb}' {filename} 123", True),
                       (f"'' {filename} 123", True),
                       ("'' selkies_2.1.0_amd64.deb 123", False),
                       ("'' another_1.0_amd64.deb 123", False),
                       (f"'file:/tmp/untrusted.deb' {filename} 123", False),
                       (f"'file://untrusted{deb}' {filename} 123", False)]
            for output, allowed in entries:
                with patch.object(CORE, 'BASE', base), \
                     patch.object(CORE, 'capture', side_effect=[metadata, f'Inst selkies ({version})', output]), \
                     patch.object(CORE, 'logged') as run:
                    if allowed:
                        CORE.safe_apt_install([str(deb)], validated_local_deb=deb)
                        run.assert_called_once()
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'origen'):
                            CORE.safe_apt_install([str(deb)], validated_local_deb=deb)
                        run.assert_not_called()
            with patch.object(CORE, 'capture', side_effect=[f'Inst selkies ({version})', entries[0][0]]), \
                 patch.object(CORE, 'logged') as run:
                with self.assertRaisesRegex(RuntimeError, 'origen'):
                    CORE.safe_apt_install([str(deb)])
                run.assert_not_called()
            for wrong_version in ('2.1.0', '2.1.0-2~ubuntu24.04', '99.0'):
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

    def test_audio_profile_stable_under_load(self):
        conf = CORE.audio_daemon_conf()
        for line in ('default-sample-rate = 48000', 'alternate-sample-rate = 48000',
                     'default-sample-format = s16le', 'flat-volumes = no',
                     'resample-method = speex-float-1',
                     'default-fragments = 4', 'default-fragment-size-msec = 40'):
            self.assertIn(line, conf)
        self.assertIn('rate=48000', CORE.AUDIO_SINK_ARGS)
        self.assertIn('format=s16le', CORE.AUDIO_SINK_ARGS)
        self.assertIn('channels=2', CORE.AUDIO_SINK_ARGS)
        # |locked is bool-only; enums take one value; int/float are plain numbers.
        core_source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        for pair in ("SELKIES_AUDIO_BITRATE='96000'",
                     "SELKIES_AUDIO_CHANNELS='2'",
                     "SELKIES_AUDIO_FRAME_DURATION_MS='20'",
                     "SELKIES_AUDIO_REDUNDANCY_DISTANCE='2'"):
            self.assertIn(pair, core_source)
        for invalid in ("AUDIO_FRAME_DURATION_MS='20|locked'", "AUDIO_BITRATE='96000|locked'",
                        "AUDIO_CHANNELS='2-2'", "AUDIO_REDUNDANCY_DISTANCE='2-2'"):
            self.assertNotIn(invalid, core_source)
        # One queued chunk drops audio on the first hiccup; 90 bounds latency while absorbing bursts.
        self.assertEqual(inspect.signature(CORE.bootstrap)
                         .parameters['backpressure_queue_size'].default, 90)
        with self.assertRaisesRegex(ValueError, 'cola: 1–100000'):
            CORE.bootstrap(backpressure_queue_size=100001)

    def test_spawn_lowers_audio_priority_before_dropping_privileges(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(CORE, 'BASE', Path(folder)), \
             patch.object(subprocess, 'Popen') as popen:
            CORE.spawn(['pulseaudio', '--version'], 'pulse', {}, {}, nice=-10)
            command = popen.call_args.args[0]
            self.assertEqual(command[:3], ['nice', '-n', '-10'])
            self.assertTrue(command[3].endswith('runuser'))
            self.assertEqual(command[4], '-u')
            self.assertIn('pulseaudio', command)

    def test_capture_cell_uses_only_real_settings(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Optimización de captura y stream')
        source = ''.join(cell['source'])
        # Selkies 2.0 already decodes with WebCodecs; window.SELKIES_CONFIG does
        # not exist and PIXELFLUX_NVENC_* profile/preset/bframes are not settings.
        for forbidden in ('SELKIES_CONFIG', 'PIXELFLUX_NVENC_PROFILE', 'PIXELFLUX_NVENC_PRESET',
                          'PIXELFLUX_NVENC_TUNING', 'PIXELFLUX_NVENC_RC_MODE',
                          'PIXELFLUX_NVENC_BFRAMES', 'B-frames', 'Perfil Main'):
            self.assertNotIn(forbidden, source)
        for required in ('VideoDecoder', 'restore_libxcb', "'--video-min-qp'",
                         "'--video-max-qp'", "'--audio-frame-duration-ms'",
                         "'--audio-redundancy'", "'--keyframe-interval'"):
            self.assertIn(required, source)
        # The audio queue is inherited from the start cell and must not be reset.
        self.assertNotIn('--backpressure-queue-size', source)
        # No emoji or pictographic decoration in any cell.
        for index, cell in enumerate(document['cells']):
            for character in ''.join(cell['source']):
                point = ord(character)
                decorative = (point in (0xfe0f, 0x200d) or 0x1f000 <= point <= 0x1faff
                              or 0x2600 <= point <= 0x27bf or 0x2b00 <= point <= 0x2bff)
                self.assertFalse(decorative, f'emoji {character!r} en la celda {index}')

    def test_pinned_versions_and_sha256(self):
        self.assertEqual(CORE.SELKIES_VERSION, '2.1.0')
        self.assertEqual(CORE.SELKIES_DEB_VERSION, '2.1.0-1~ubuntu24.04')
        self.assertEqual(CORE.CLOUDFLARED_VERSION, '2026.10.3')
        self.assertEqual(CORE.CHROME_VERSION, '156.0.8078.47-1')
        self.assertEqual(len(CORE.CHROME_SHA256), 64)
        self.assertFalse(CORE.CLOUDFLARED_URL.endswith('/latest/download/cloudflared-linux-amd64'))
        with tempfile.TemporaryDirectory() as folder:
            sample = Path(folder) / 'sample'
            sample.write_bytes(b'pc-free-t4')
            good = hashlib.sha256(b'pc-free-t4').hexdigest()
            CORE.require_sha256(sample, good)
            self.assertTrue(sample.exists())
            with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
                CORE.require_sha256(sample, '0' * 64)
            self.assertFalse(sample.exists())

    def test_selkies_21_profile_is_explicit(self):
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        for flag in ("('true' if congestion_control else 'false')", '--frame-ancestors=self',
                     '--use-paint-over-quality=false', '--second-screen=false',
                     '--audio-bitrate=96000', '--audio-channels=2',
                     '--rate-control-mode=cbr', '--keyframe-interval=0',
                     '--video-streaming-mode=true', '--video-fullcolor=false',
                     '--enable-resize=true'):
            self.assertIn(flag, source)
        self.assertNotIn("install_pixelflux_libxcb_guard", source)
        self.assertIn('def verify_pixelflux(', source)
        self.assertIn('Virtual MAX_WIDTH MAX_HEIGHT', source)
        self.assertIn('max(width, 1920)', source)
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, start = find_cell(document, '# @title Iniciar PC-Free-T4')
        self.assertIn('BACKPRESSURE_QUEUE_SIZE = 90', ''.join(start['source']))
        self.assertIn('FPS_CAP = 60', ''.join(start['source']))

    def test_game_environment_cell_is_real_and_clean(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Entorno global de juegos')
        source = ''.join(cell['source'])
        for good in ('DXVK_SHADER_CACHE_PATH', 'VKD3D_SHADER_CACHE_PATH',
                     "'.config' / 'pcfree'", "'game.env'"):
            self.assertIn(good, source)
        for bad in ('DXVK_ASYNC', 'VKD3D_SHADER_CACHE=', 'PROTON_NO_ESYNC',
                    'PROTON_NO_FSYNC', 'WINEPREFIX', 'MESA_VK_WSI_PRESENT_MODE'):
            self.assertNotIn(bad, source)

    def test_ge_proton_and_proton_test_cells(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, ge_cell = find_cell(document, 'Instalar GE-Proton')
        _, probe_cell = find_cell(document, 'Pruebas de compatibilidad de Proton')
        ge = ''.join(ge_cell['source'])
        probe = ''.join(probe_cell['source'])
        self.assertIn('INSTALL_GE_PROTON = False', ge)
        self.assertIn('install_ge_proton', ge)
        for token in ('-m32', '-m64', 'vkCreateInstance', 'GE-Proton11-11',
                      "'run'", "'cmd'"):
            self.assertIn(token, probe)
        self.assertIn('STEAM_COMPAT_DATA_PATH', probe)

    def test_optional_install_does_not_abort_on_conflict(self):
        calls = []
        def attempt(packages):
            calls.append(packages)
            if len(calls) == 1 or packages == ['a']:
                raise RuntimeError('APT propone eliminar libejemplo; operación cancelada.')
        with patch.object(CORE, 'safe_apt_install', side_effect=attempt):
            CORE.safe_optional_install(['a', 'b'], 'prueba')
        self.assertEqual(calls, [['a', 'b'], ['a'], ['b']])

    def test_chrome_verification_cell_uses_absolute_runuser(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Verificar Chrome y navegador predeterminado')
        source = ''.join(cell['source'])
        self.assertIn("PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'", source)
        self.assertIn("shutil.which('runuser')", source)
        self.assertIn('except (FileNotFoundError, subprocess.SubprocessError)', source)

    def test_app_installer_cell_and_helper(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Instalador de .deb, .AppImage')
        source = ''.join(cell['source'])
        for token in ('application/x-appimage', 'application/vnd.debian.binary-package',
                      'application/x-rpm', 'APPIMAGE_EXTRACT_AND_RUN', 'pcfree-install-deb',
                      'xdg-mime', 'Descargar aplicación', 'runuser', 'rpm2cpio',
                      'install_tar', 'install_rpm', '.tar.gz'):
            self.assertIn(token, source)
        helper = re.search(r"helper\.write_text\(r'''(.*?)'''\)", source, re.S)
        self.assertIsNotNone(helper)
        ast.parse(helper.group(1))

    def test_heroic_cell_installs_wine_and_game_dependencies(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Instalar Heroic, Wine 9')
        source = ''.join(cell['source'])
        for token in ('wine32:i386', 'libwine:i386', 'winetricks', 'cabextract',
                      'libvulkan1:i386', 'libgtk-3-0t64', 'libnss3', 'curl',
                      'GE-Proton9-27', 'wineVersion', 'autoInstallDxvk',
                      'autoInstallVkd3d', 'INSTALL_HEROIC_PROTON = True'):
            self.assertIn(token, source)
        self.assertNotIn('usuario', source.lower())
        ast.parse(source)

    def test_congestion_control_switch(self):
        parameters = inspect.signature(CORE.bootstrap).parameters
        self.assertIs(parameters['congestion_control'].default, False)
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        # El flag debe llegar al argv y a la sesion, no solo existir el nombre.
        self.assertIn("'--congestion-control=' + ('true' if congestion_control else 'false')", source)
        self.assertIn("'congestion_control': congestion_control,", source)
        with self.assertRaisesRegex(ValueError, 'congestion_control'):
            CORE.bootstrap(congestion_control='yes')
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, start = find_cell(document, '# @title Iniciar PC-Free-T4')
        cell = ''.join(start['source'])
        self.assertIn('ENABLE_CONGESTION_CONTROL = False', cell)
        self.assertIn('congestion_control=ENABLE_CONGESTION_CONTROL', cell)

    def test_fps_cap_writes_real_dxvk_keys(self):
        self.assertEqual(inspect.signature(CORE.bootstrap).parameters['fps_cap'].default, 60)
        with self.assertRaisesRegex(ValueError, 'fps_cap'):
            CORE.bootstrap(fps_cap=300)
        account = types.SimpleNamespace(pw_uid=1000, pw_gid=1000)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(CORE.pwd, 'getpwnam', return_value=account), \
             patch.object(CORE.os, 'chown'):
            session = {'home': folder, 'env': {}}
            config = CORE.apply_fps_cap(session, {}, 60)
            text = Path(config).read_text()
            self.assertIn('dxvk.maxFrameRate = 60', text)
            self.assertIn('d3d9.maxFrameRate = 60', text)
            self.assertIn('dxgi.maxFrameRate = 60', text)
            self.assertEqual(session['env']['VKD3D_FRAME_RATE'], '60')
            self.assertEqual(session['env']['DXVK_CONFIG_FILE'], str(config))
            CORE.apply_fps_cap(session, {}, 0)
            self.assertNotIn('VKD3D_FRAME_RATE', session['env'])
            self.assertNotIn('maxFrameRate', Path(config).read_text())
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        for invented in ('dxvk.framerate', 'WINE_FULLSCREEN_FPS', "DXVK_FRAME_RATE'"):
            self.assertNotIn(invented, source)

    def test_gamepad_provisioning_logic(self):
        # fake-udev ships no binaries in the .deb: it must be built from the pinned
        # source, and a 64-bit build alone must be enough for Chrome, Heroic and SDL2.
        self.assertEqual(CORE.SELKIES_SRC_SHA256,
                         '67eaae6f175df845f8dd7fffc58911dcaa5b9f07150f129e314ca45d47405b40')
        self.assertEqual(CORE.GAMEPAD_TRIPLETS['amd64'], 'x86_64-linux-gnu')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'fake-udev'
            self.assertEqual(CORE.gamepad_preload(root), (None, None, []))
            target = root / 'lib' / 'x86_64-linux-gnu'
            target.mkdir(parents=True)
            (target / 'libudev.so.1').write_bytes(b'fake')
            interposer, fake, arches = CORE.gamepad_preload(root)
            self.assertIsNone(interposer)
            self.assertEqual(fake, str(root / '$LIB' / 'libudev.so.1'))
            self.assertEqual(arches, ['amd64'])
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertIn("'make', '-C', str(build), target", source)
        self.assertIn("('amd64', 'all', 'libudev.so.1.0.0-fake')", source)
        self.assertIn("('i386', 'all32', 'libudev_x86.so.1.0.0-fake')", source)
        self.assertIn('fake_udev_root', source)
        # The launcher must only use the SDL fallback when fake-udev is missing.
        launcher = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertIn('interposer_ready', launcher)

    def test_elf_arch_detection(self):
        self.assertEqual(CORE.elf_arch('/bin/sh'), 'amd64')
        self.assertIsNone(CORE.elf_arch('/etc/hostname'))
        self.assertIsNone(CORE.elf_arch('/nonexistent/file'))

    def test_fsr_and_shader_tuning(self):
        account = types.SimpleNamespace(pw_uid=1000, pw_gid=1000)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(CORE.pwd, 'getpwnam', return_value=account), \
             patch.object(CORE.os, 'chown'):
            session = {'home': folder, 'env': {}}
            config = CORE.apply_fps_cap(session, {}, 60, True, 2)
            text = Path(config).read_text()
            self.assertIn('dxvk.enableGraphicsPipelineLibrary = Auto', text)
            self.assertIn('dxvk.numCompilerThreads = 1', text)
            self.assertIn('dxvk.tearFree = False', text)
            self.assertEqual(session['env']['WINE_FULLSCREEN_FSR'], '1')
            self.assertEqual(session['env']['WINE_FULLSCREEN_FSR_STRENGTH'], '2')
            self.assertEqual(session['env']['VKD3D_CONFIG'], 'pipeline_library_app_cache')
            self.assertIn('VKD3D_SHADER_CACHE_PATH', session['env'])
            CORE.apply_fps_cap(session, {}, 60, False, 2)
            self.assertNotIn('WINE_FULLSCREEN_FSR', session['env'])
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        # The async pipeline patch and DXVK_FRAME_RATE no longer exist in DXVK.
        self.assertNotIn('DXVK_ASYNC', source)
        self.assertNotIn("env['DXVK_FRAME_RATE']", source)
        with self.assertRaisesRegex(ValueError, 'fsr_strength'):
            CORE.bootstrap(fsr_strength=9)

    def test_start_cell_exposes_fsr(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, start = find_cell(document, '# @title Iniciar PC-Free-T4')
        cell = ''.join(start['source'])
        for token in ('FSR_UPSCALING = False', 'FSR_STRENGTH = 2',
                      'fsr=FSR_UPSCALING', 'fsr_strength=FSR_STRENGTH',
                      'FSR 2/3 dependen del juego o un mod'):
            self.assertIn(token, cell)

    def test_language_server_watchdog(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'pcfree-noise-guard')
        source = ''.join(cell['source'])
        for token in ('pyright-langserver', 'pkill -f', 'sleep 20',
                      "Path('/usr/local/sbin/pcfree-noise-guard')", 'setsid'):
            self.assertIn(token, source)
        self.assertIn('noise-guard.pid', source)

    def test_deb_helper_resolves_dependencies(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        source = ''.join(document['cells'][3]['source'])
        helper = re.search(r'helper\.write_text\("""(#!/usr/bin/python3\.12.*?)"""\)', source, re.S)
        self.assertIsNotNone(helper)
        body = helper.group(1)
        ast.parse(body)
        # Recommends carry fonts and audio for desktop apps; --fix-broken repairs deps.
        self.assertNotIn('--no-install-recommends', body)
        self.assertIn('--fix-broken', body)
        self.assertIn('Remv ', body)
        self.assertIn('nvidia', body)
        for uri_guard in ('archive.ubuntu.com', 'ports.ubuntu.com'):
            self.assertIn(uri_guard, body)

    def test_battly_cell_pinned_and_functional(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'INSTALL_BATTLY')
        source = ''.join(cell['source'])
        for token in ("BATTLY_VERSION = '3.0.1'",
                      "'9fefe53b19ac0d6b2571e7783d95092e4a401ab198b6bae36edff1de48230e01'",
                      'Battly-Launcher-linux-amd64.deb', 'battlylauncher',
                      'openjdk-21-jre-headless', '/opt/Battly Launcher/battlylauncher',
                      '--no-sandbox', 'pcfree-battly', 'Battly.desktop',
                      'unshare', 'Sodium', 'VulkanMod'):
            self.assertIn(token, source)
        self.assertNotIn('--no-install-recommends', source)
        ast.parse(source)

    def test_no_broken_code_paths(self):
        # Fallos detectados en auditoría: cada uno rompía la ejecución real.
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        cells = [''.join(c['source']) for c in document['cells'] if c['cell_type'] == 'code']

        # 1) Battly: Path concatenado a str -> TypeError tras descargar 107 MB.
        battly = next(c for c in cells if 'INSTALL_BATTLY' in c)
        self.assertNotIn("+ 'Exec=' + wrapper + ", battly)
        self.assertIn('str(wrapper)', battly)

        # 2) Prioridades: la celda debe conservar imports y renice/ionice.
        priority = next(c for c in cells if 'pcfree-noise-guard' in c)
        self.assertIn('import os, subprocess', priority)
        self.assertIn('from pathlib import Path', priority)
        self.assertIn('def set_priority', priority)
        self.assertIn('renice', priority)
        self.assertIn('os.geteuid() != 0', priority)

        # 3) Sonda C: printf con salto de linea real rompe gcc.
        probe = next(c for c in cells if 'probe_c = ' in c)
        literal = re.search(r"probe_c = r'''(.*?)'''", probe, re.S).group(1)
        self.assertNotIn('printf("\n")', literal)
        self.assertIn('printf("\\n")', literal)
        self.assertIn('def as_user', probe)

        # 4) Steam: proot-bwrap devuelve 404 y la validacion era imposible.
        steam = next(c for c in cells if 'INSTALL_STEAM = True' in c)
        self.assertNotIn('_prepare_proot_bwrap', steam)
        self.assertNotIn('proot-bwrap/commits', steam)
        self.assertIn("'runuser'", steam)

        # 5) Heroic: config.json se crea aunque no exista.
        heroic = next(c for c in cells if 'INSTALL_HEROIC' in c)
        self.assertIn("config = {}", heroic)
        self.assertIn("config.setdefault('version', 'v0')", heroic)
        self.assertNotIn('if True:', heroic)
        self.assertIn('--no-sandbox', heroic)

        # 6) Instalador: el finally borraba la extraccion antes de buscar iconos.
        installer = next(c for c in cells if 'pcfree-app-installer' in c)
        self.assertLess(installer.index('Respaldo de icono dentro del try'),
                        installer.index('shutil.rmtree(extract'))
        self.assertIn("lambda _match: 'Exec=' + command", installer)
        self.assertIn('--no-absolute-filenames', installer)
        self.assertNotIn("'application/gzip'", installer)

        # 7) Limpieza: no puede borrar las caches que usan DXVK/VKD3D/GE-Proton.
        cleanup = next(c for c in cells if 'Liberar espacio' in c)
        self.assertIn("'pcfree'", cleanup)
        self.assertNotIn("'/tmp/pcfree-selkies/*'", cleanup)

        # 8) Celda 8 no debe perder el sufijo |locked de Selkies.
        stream = next(c for c in cells if 'apply_settings(argv, wanted, title)' in c)
        self.assertIn("'|locked' if", stream)

    def test_helper_and_scripts_have_imports(self):
        import ast as _ast
        for name in ('10-export-worlds.py', '11-restore-worlds.py'):
            source = (ROOT / 'scripts' / name).read_text()
            tree = _ast.parse(source)
            imported = {alias.name for node in _ast.walk(tree)
                        if isinstance(node, _ast.Import) for alias in node.names}
            imported |= {alias.name for node in _ast.walk(tree)
                         if isinstance(node, _ast.ImportFrom) for alias in node.names}
            for required in ('Path', 'shutil'):
                self.assertIn(required, imported, f'{name}: falta {required}')
        desktop = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertNotIn("return ['runuser', '-u', USER", desktop)
        self.assertIn("shutil.which('runuser')", desktop)
        for path in (ROOT / 'scripts').glob('*.py'):
            for call in _ast.walk(_ast.parse(path.read_text())):
                if (isinstance(call, _ast.Call) and getattr(call.func, 'attr', '') == 'extractall'):
                    keywords = {kw.arg for kw in call.keywords}
                    self.assertIn('filter', keywords, f'{path.name}: extractall sin filter')

    def test_stream_mode_forced_on_reload(self):
        # Un modo guardado en localStorage (p. ej. webrtc) o selkies_mode_flip
        # en sessionStorage dejaban la pagina en "conectando" tras recargar.
        self.assertIn('pcfree-stream-mode', CORE.STREAM_MODE_JS)
        self.assertIn('__SELKIES_STREAMING_MODE__', CORE.STREAM_MODE_JS)
        self.assertIn("sessionStorage.removeItem(\"selkies_mode_flip\")", CORE.STREAM_MODE_JS)
        self.assertIn('stream_mode', CORE.STREAM_MODE_JS)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'upstream'
            source.mkdir()
            (source / 'assets').mkdir()
            (source / 'index.html').write_text(
                '<!doctype html><html><head><script type="module" src="./assets/app.js"></script>'
                '</head><body></body></html>')
            with patch.object(CORE, 'BASE', Path(folder) / 'state'):
                target = Path(CORE.prepare_web_client(source))
                html = (target / 'index.html').read_text()
                self.assertEqual(html.count('<script id="pcfree-stream-mode">'), 1)
                # Debe ejecutarse antes que el bundle del cliente.
                self.assertLess(html.index('pcfree-stream-mode'), html.index('assets/app.js'))
                CORE.prepare_web_client(source)
                again = (target / 'index.html').read_text()
                self.assertEqual(again.count('<script id="pcfree-stream-mode">'), 1)
                self.assertEqual(again.count('<script src="./pcfree-input-guard.js">'), 1)
        chrome = (ROOT / 'scripts/selkies-desktop.py').read_text()
        for flag in ('--enable-gpu-rasterization', '--enable-zero-copy'):
            self.assertIn(flag, chrome)

    def test_security_static(self):
        source = (ROOT / 'scripts/selkies-desktop.py').read_text()
        self.assertIn('--addr=127.0.0.1', source)
        self.assertIn('--enable-basic-auth=true', source)
        self.assertIn("'--protocol', 'http2'", source)
        self.assertIn("server_env.pop('LD_PRELOAD', None)", source)
        self.assertIn("server_env['LD_PRELOAD'] = shm_perms", source)
        self.assertIn('shm_perms = shm_perms_library()', source)
        self.assertIn("--backpressure-queue-size=", source)
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

    def test_preparation_cell_publishes_patched_core(self):
        # Cell 3 must publish its patched source; otherwise bootstrap() recompiles
        # the unpatched SOURCES and every [OK] printed by the cell is a lie.
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        env = {}
        _, kernel_cell = find_cell(document, 'Cargar núcleo interno')
        _, preparation_cell = find_cell(document, 'Preparación del escritorio')
        exec(compile(''.join(kernel_cell['source']), 'cell2', 'exec'), env)
        original = env['SOURCES']['selkies-desktop.py']
        preparation = ''.join(preparation_cell['source'])
        exec(compile(preparation, 'preparation', 'exec'), env)
        patched = env['SOURCES']['selkies-desktop.py']
        self.assertNotEqual(patched, original)
        compile(patched, 'patched-core', 'exec')
        for marker in ('def add_i386_nvidia(', 'def desktop_launchers(',
                       'Option "HardDPMS" "false"',
                       'SELKIES_AUDIO_FRAME_DURATION_MS', 'pcfreeInputGuard = {version: 2',
                       "SELKIES_AUDIO_BITRATE='96000'", 'flat-volumes = no',
                       'default-fragment-size-msec = 40',
                       "pcfree-install-deb' + chr(10)"):
            self.assertIn(marker, patched)
        self.assertTrue(callable(env['_core'].get('bootstrap')))
        tree = ast.parse(patched)
        desktop_files = next(node for node in tree.body
                             if isinstance(node, ast.FunctionDef) and node.name == 'desktop_files')
        self.assertTrue(any(isinstance(node, ast.Call)
                            and getattr(node.func, 'id', None) == 'desktop_launchers'
                            for node in ast.walk(desktop_files)))
        # Re-running the preparation must not duplicate patches nor drop the core.
        exec(compile(preparation, 'preparation-again', 'exec'), env)
        self.assertEqual(env['SOURCES']['selkies-desktop.py'], patched)
        self.assertTrue(callable(env['_core'].get('bootstrap')))

        # The injected helpers must be runnable, not just parseable.
        core = env['_core']
        writes = {}
        class NoThread:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass
        session = {'home': '/fictional', 'user': 'pcfree-browser',
                   'run_launcher': '/usr/local/bin/pcfree-run'}
        shortcuts = []
        with patch.object(Path, 'write_text', lambda self, text, **kw: writes.__setitem__(str(self), text)), \
             patch.object(Path, 'chmod'), \
             patch.dict(core, {'logged': lambda *a, **k: None,
                               'safe_apt_install': lambda *a, **k: None,
                               'shortcut': lambda *a, **k: shortcuts.append(a[1])}), \
             patch.object(core['threading'], 'Thread', NoThread):
            core['desktop_launchers'](session)
        self.assertIn('pcfree-install-deb', ''.join(writes))
        self.assertIn('#!/usr/bin/python3.12', writes['/usr/local/sbin/pcfree-install-deb'])
        self.assertIn('NOPASSWD: /usr/local/sbin/pcfree-install-deb',
                      writes['/etc/sudoers.d/pcfree-deb'])
        self.assertEqual(shortcuts, ['Instalar-DEB', 'ProtonUp-Qt'])
        with patch.dict(core, {'logged': Mock(side_effect=RuntimeError('apt no disponible'))}):
            self.assertEqual(core['add_i386_nvidia']('580.82.07', '/fictional', '/libraries'),
                             '/libraries')

    def test_cleanup_cell_keeps_active_tunnel_and_apt_metadata(self):
        document = json.loads((ROOT / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
        _, cell = find_cell(document, 'Liberar espacio')
        source = ''.join(cell['source'])
        # Deleting the binary before checking pgrep would break the next start.
        self.assertLess(source.index("'pgrep'"),
                        source.index("clean(str(BASE / 'cloudflared')"))
        for flag in ('if KEEP_APT_LISTS:', 'if REMOVE_DOCS:', 'if ALLOW_AUTOREMOVE:'):
            self.assertIn(flag, source)

    def test_builder_deterministic_and_preserves_backup(self):
        target = ROOT / 'PC-Free-T4.ipynb'
        before = target.read_bytes()
        subprocess.run(['python3', str(ROOT / 'tools/build-notebooks.py')], check=True)
        self.assertEqual(before, target.read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
