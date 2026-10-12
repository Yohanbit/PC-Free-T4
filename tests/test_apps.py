"""Offline optional installer checks. No downloads or software installation."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/compat-apps.py'
spec = importlib.util.spec_from_file_location('pcfree_optional', path)
module = importlib.util.module_from_spec(spec)
with patch.object(subprocess, 'run', side_effect=AssertionError('Import triggered installation')):
    spec.loader.exec_module(module)
assert {'blender', 'wine', 'java', 'lutris'} <= module.OPTIONS.keys()
assert {'godot', 'vinegar', 'roblox'} <= module.EXPERIMENTAL

session = {'user': 'offline', 'home': '/tmp/unused-home', 'env': {}}
with patch.object(module.os, 'geteuid', return_value=0):
    with patch.object(module, 'install_godot') as godot, patch.object(module, 'install_vinegar') as vinegar, patch.object(module, 'install_roblox') as roblox:
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, 'BASE', Path(directory)):
                module.install_app('godot', session)
                module.install_app('vinegar', session)
                module.install_app('roblox', session)
        godot.assert_called_once_with(session)
        vinegar.assert_called_once_with(session)
        roblox.assert_called_once_with(session)

with patch.object(module, 'sober_requirements', return_value={}), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Operation not permitted')) as run, patch.object(module, 'command') as install:
    try:
        module.install_roblox(session)
    except RuntimeError as error:
        assert 'sandbox' in str(error)
    else:
        raise AssertionError('Roblox attempted without namespaces')
    install.assert_not_called()
    assert 'unshare' in run.call_args.args[0]

assert module.sober_requirements('flags : sse4_1 sse4_2\n', 'x86_64', '6.8.0')['sse4_2']
assert not module.sober_requirements('flags : sse4_1\n', 'x86_64', '5.11.0')['sse4_2']
for cpu, machine, kernel in [('flags : sse2\n', 'x86_64', '6.8'), ('flags : sse4_1\n', 'aarch64', '6.8'), ('flags : sse4_1\n', 'x86_64', '5.10')]:
    try:
        module.sober_requirements(cpu, machine, kernel)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Unsupported Sober hardware accepted')

with tempfile.TemporaryDirectory() as directory:
    attempted = []
    def deny_proc(argv, *args, **kwargs):
        attempted.append(argv)
        if 'bwrap' in argv:
            raise RuntimeError("Can't mount proc: Permission denied")
    with patch.object(module, 'BASE', Path(directory)), patch.object(module, 'sober_requirements', return_value={}), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), patch.object(module, 'command', side_effect=deny_proc):
        try:
            module.install_roblox({**session, 'driver_version': '580.82.07'})
        except RuntimeError as error:
            assert '/proc' in str(error)
        else:
            raise AssertionError('Denied proc mount accepted')
    assert not any('org.vinegarhq.Sober' in call or 'remote-add' in call for call in attempted), 'Large downloads before real sandbox validation'

with tempfile.TemporaryDirectory() as directory:
    with patch.object(module, 'BASE', Path(directory)), patch.object(module, 'sober_requirements', return_value={'sse4_1': True}), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), patch.object(module, 'command') as commands, patch.object(module, 'shortcut') as desktop:
        module.install_roblox({**session, 'driver_version': '580.82.07', 'env': {'LD_LIBRARY_PATH': '/host/private', 'VK_DRIVER_FILES': '/host/icd.json'}})
        calls = [call.args[0] for call in commands.call_args_list]
        assert any('org.freedesktop.Platform.GL.nvidia-580-82-07//1.4' in call for call in calls)
        assert any('--command=true' in call for call in calls)
        assert not any('/host/private' in str(call) or '/host/icd.json' in str(call) for call in calls)
        wrapper = Path(directory, 'apps/sober-launch').read_text()
        assert '-u LD_PRELOAD' in wrapper and 'nvidia-580-82-07:default' in wrapper
        assert json.loads(Path(directory, 'sober-requirements.json').read_text())['game_validated'] is False

with tempfile.TemporaryDirectory() as directory:
    log = Path(directory) / 'install.log'
    for plan in ('Remv xfce4-session [1.0]', 'Inst nvidia-driver-580 (580.0 official)', 'Inst linux-image-generic (6.8 official)'):
        with patch.object(module.subprocess, 'check_output', return_value=plan), patch.object(module.subprocess, 'run') as run:
            try:
                module.command(['apt-get', 'install', 'blender'], log)
            except RuntimeError:
                pass
            else:
                raise AssertionError('Unsafe dependency plan accepted')
            run.assert_not_called()
    bad_origin = "'https://unknown.example/blender.deb' blender.deb 20 SHA256:abc"
    with patch.object(module.subprocess, 'check_output', side_effect=['Inst blender (4.0 official)', bad_origin]), patch.object(module.subprocess, 'run') as run:
        try:
            module.command(['apt-get', 'install', 'blender'], log)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unofficial source accepted')
        run.assert_not_called()
    with patch.object(module.subprocess, 'check_output', side_effect=['Inst blender (4.0 official)', "'http://archive.ubuntu.com/ubuntu/blender.deb' blender.deb 20 SHA256:abc"]), patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run:
        module.command(['apt-get', 'install', 'blender'], log)
        assert run.call_count == 1
        assert 'LD_PRELOAD' not in run.call_args.kwargs['env']

tree = ast.parse(path.read_text())
assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'Popen' for node in ast.walk(tree)), 'Optional installer must not start background graphical applications'
print('PASS: side-effect-free imports, optional dispatch, Roblox sandbox refusal, safe APT plans/origins, no graphical autostart.')
