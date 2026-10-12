"""Offline optional installer checks. No downloads or software installation."""
import ast
import importlib.util
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

with patch.object(module.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'Operation not permitted')) as run, patch.object(module, 'command') as install:
    try:
        module.install_roblox(session)
    except RuntimeError as error:
        assert 'sandbox' in str(error)
    else:
        raise AssertionError('Roblox attempted without namespaces')
    install.assert_not_called()
    assert 'unshare' in run.call_args.args[0]

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
