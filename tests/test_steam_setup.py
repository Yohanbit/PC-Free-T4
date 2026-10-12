"""Pruebas offline: no APT, red, Steam, escritorio ni sesión real."""
import contextlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/compat-steam.py'
spec = importlib.util.spec_from_file_location('pcfree_optional', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.install_steam)
checks = []

with patch.dict(module.os.environ, {'LD_LIBRARY_PATH': '/host/nvml', 'LD_PRELOAD': '/bad.so'}), \
     patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='580.82.07')) as run:
    module._run(['nvidia-smi'], env={'LD_LIBRARY_PATH': '/session/gpu'}, host_gpu=True)
    env = run.call_args.kwargs['env']
    assert env['LD_LIBRARY_PATH'] == '/session/gpu:/host/nvml:/usr/lib64-nvidia'
    assert 'LD_PRELOAD' not in env
    module._run(['apt-get', 'update'])
    assert 'LD_LIBRARY_PATH' not in run.call_args.kwargs['env']
    assert 'APT::Get::AllowUnauthenticated=false' in run.call_args.args[0]
    module._run(['make'])
    assert 'LD_LIBRARY_PATH' not in run.call_args.kwargs['env']
    try:
        module._run(['make'], host_gpu=True)
    except ValueError:
        pass
    else:
        raise AssertionError('host_gpu allowed for build')
checks.append('Colab NVML env preserved only for nvidia-smi; APT/build clean and authenticated')

official = 'https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/./libnvidia.deb'
assert module._official_apt_uri(official)
assert module._official_apt_uri('http://archive.ubuntu.com/ubuntu/pool/lib.deb')
assert module._official_apt_uri('https://us.archive.ubuntu.com/ubuntu/pool/lib.deb')
for bad in ['https://evil.example/lib.deb', official.replace('/./', '/../'),
            official.replace('/./', '/%2e%2e/'), official.replace('https:', 'http:'),
            official.replace('ubuntu2404', 'ubuntu2204'), official + '?source=untrusted']:
    assert not module._official_apt_uri(bad), bad
checks.append('official APT origins including NVIDIA /./ and traversal rejection')

for plan in ['Inst nvidia-driver-580 (580 repo)', 'Inst libnvidia-gl-580:i386 (580 repo)',
             'Inst linux-image-6.8.0 (1 repo)', 'Inst linux-modules-6.8.0 (1 repo)',
             'Remv libudev1 [1]']:
    with patch.object(module, '_run', return_value=plan) as run:
        try:
            module._safe_install(['libudev1:i386'], None)
        except RuntimeError:
            pass
        else:
            raise AssertionError('unsafe plan accepted')
        assert run.call_count == 1
with patch.object(module, '_run', side_effect=['Inst libudev1:i386 (1 repo)', "'https://evil.example/x.deb' x.deb 10 SHA256:a"]) as run:
    try:
        module._safe_install(['libudev1:i386'], None)
    except RuntimeError:
        pass
    else:
        raise AssertionError('unsafe install origin accepted')
    assert run.call_count == 2
checks.append('APT simulation blocks GPU/kernel/removals and nonofficial install origins')

with tempfile.TemporaryDirectory(prefix='steam-offline-') as temporary:
    root = Path(temporary)
    calls = []
    def origins_run(argv, **kwargs):
        calls.append(argv)
        if argv[:2] == ['apt-cache', 'madison']:
            return 'libnvidia-gl-580 | 580.82.07-0ubuntu1 | official'
        if argv[:2] == ['apt-cache', 'show']:
            return 'Package: libnvidia-gl-580'
        if '--print-uris' in argv:
            uri = official if ':amd64=' in argv[-1] else 'https://evil.example/x.deb'
            return "'" + uri + "' x.deb 10 SHA256:a"
        raise AssertionError('download/extract occurred before all origins validated')
    with patch.object(module, '_run', side_effect=origins_run):
        try:
            module._graphics(root, '580.82.07', None)
        except RuntimeError:
            pass
        else:
            raise AssertionError('unsafe NVIDIA origin accepted')
    assert not any(argv[:2] == ['apt-get', 'download'] for argv in calls)
    checks.append('both NVIDIA architectures origins validated before any download')
    for arch, elf_class, machine in [('amd64', 2, 62), ('i386', 1, 3)]:
        library = root / arch
        header = bytearray(20)
        header[:4] = b'\x7fELF'
        header[4:6] = bytes([elf_class, 1])
        header[18:20] = struct.pack('<H', machine)
        library.write_bytes(header)
        module._elf(library, arch)
        with contextlib.suppress(RuntimeError):
            module._elf(library, 'i386' if arch == 'amd64' else 'amd64')
            raise AssertionError('wrong ELF accepted')
    checks.append('ELF amd64/i386 validation')

    with patch.object(module, '_run', return_value='libnvidia-gl-580 | 580.82.07-0ubuntu1 | official'):
        assert module._exact_package('libnvidia-gl-580', 'i386', '580.82.07', None) == '580.82.07-0ubuntu1'
        try:
            module._exact_package('libnvidia-gl-580', 'i386', '580.99.99', None)
        except RuntimeError:
            pass
        else:
            raise AssertionError('mismatched driver accepted')
    checks.append('exact version / missing version refusal')

    home = root / 'home'
    client = home / '.local/share/Steam'
    for name in ['ubuntu12_32', 'ubuntu12_64', 'config', 'userdata', 'steamapps', 'logs', 'package']:
        (client / name).mkdir(parents=True, exist_ok=True)
        (client / name / 'marker').write_text(name)
    (client / 'steam.sh').write_text('redistributable')
    base = root / 'installer'
    base.mkdir()
    quarantine = Path(module._quarantine_client(home, base))
    for name in ['config', 'userdata', 'steamapps', 'logs', 'package']:
        assert (client / name / 'marker').read_text() == name
    assert (quarantine / 'steam.sh').read_text() == 'redistributable'
    assert (quarantine / 'ubuntu12_32/marker').exists()
    checks.append('repair preserves saves/config/games/logs/update state')

    graphics = {'LD_LIBRARY_PATH': '/isolated/64:/isolated/32', 'VK_DRIVER_FILES': '/isolated/nvidia.json'}
    pads = {'SELKIES_INTERPOSER': '/usr/$LIB/selkies_input_interposer.so', 'fake_udev': '/isolated/$LIB/libudev.so.1'}
    for gamepads in ({}, pads):
        shell = module._launch_script(Path('/launcher/steam'), graphics, gamepads, None)
        path = root / 'launcher.sh'
        path.write_text(shell)
        subprocess.run(['sh', '-n', str(path)], check=True)
        assert 'dbus-run-session' in shell  # comentario explica por qué NO usarlo
        assert 'dbus-run-session --' not in shell
        assert '-cef-disable' not in shell and '--no-sandbox' not in shell
        assert 'SELKIES_BASIC_AUTH_PASSWORD' not in shell
        if gamepads:
            assert "'/usr/$LIB/selkies_input_interposer.so'" in shell
            assert "'/isolated/$LIB/libudev.so.1'" in shell
    checks.append('generated POSIX launcher / literal $LIB / no CEF or sandbox flags')

    # Simular TODO el install sin llamadas al sistema de paquetes/red/clientes.
    runtime = root / 'runtime'
    runtime.mkdir()
    runner = root / 'pcfree-run'
    runner.write_text('#!/bin/sh\nexit 0\n')
    runner.chmod(0o755)
    session = {'user': 'offline-user', 'home': str(home), 'runtime': str(runtime),
               'display': ':98', 'xauthority': str(root / 'auth'), 'gpu_root': str(root / 'gpu'),
               'driver_version': '580.82.07', 'run_launcher': str(runner)}
    session['env'] = {'HOME': str(home), 'USER': session['user'], 'DISPLAY': ':98',
                      'XAUTHORITY': session['xauthority'], 'XDG_RUNTIME_DIR': str(runtime)}
    commands = []
    def fake_run(argv, **kwargs):
        commands.append(argv)
        if argv[0] == 'nvidia-smi': return '580.82.07'
        if argv[:2] == ['apt-cache', 'search']: return 'libasound2t64 - ALSA'
        if argv[:2] == ['dpkg-deb', '-f']:
            return 'steam-launcher' if argv[-1] == 'Package' else '1.0.test'
        if argv[:2] == ['dpkg-deb', '-x']:
            extracted = Path(argv[-1]) / 'usr/lib/steam'
            extracted.mkdir(parents=True)
            (extracted / 'bin_steam.sh').write_text('#!/bin/sh\nexit 99\n')
            (extracted / 'bootstraplinux_ubuntu12_32.tar.xz').write_text('offline fixture')
        return ''
    account = SimpleNamespace(pw_uid=12345, pw_gid=12345)
    with patch.object(module, '_run', side_effect=fake_run), patch.object(module, '_download'), \
         patch.object(module, '_graphics', return_value=(graphics, [])), \
         patch.object(module.pwd, 'getpwnam', return_value=account), \
         patch.object(module.os, 'geteuid', return_value=0), patch.object(module.os, 'chown'):
        result = module.install_steam(session)
        second = module.install_steam(session)
    assert result['installed'] and not result['login_validated']
    assert (home / '.local/share/applications/pcfree-steam.desktop').exists()
    assert runner.read_text() == '#!/bin/sh\nexit 0\n'
    assert not any('steam' == Path(arg).name for command in commands for arg in command)
    assert list((home / '.local/share/pcfree/steam').glob('launcher-old-*'))
    for name in ['config', 'userdata', 'steamapps']:
        assert (client / name / 'marker').exists()
    checks.append('mock install + reinstall: no launch, pcfree-run unchanged, launcher quarantine')

    commands.clear()
    with patch.object(module, '_run', side_effect=fake_run), \
         patch.object(module, '_gamepads', return_value=pads), \
         patch.object(module, '_download') as download, \
         patch.object(module.pwd, 'getpwnam', return_value=account), \
         patch.object(module.os, 'geteuid', return_value=0), patch.object(module.os, 'chown'):
        gamepad_result = module.install_gamepads(session)
        assert not download.called
    assert gamepad_result['installed']
    assert gamepad_result['root'] == str(runtime.parent / 'fake-udev')
    assert not any(cmd[0] in ('nvidia-smi', 'dpkg-deb') for cmd in commands)
    checks.append('independent gamepad API without Steam/NVIDIA/deb download')

print(json.dumps({'passed': len(checks), 'checks': checks, 'live_session_accessed': False}, indent=2))
