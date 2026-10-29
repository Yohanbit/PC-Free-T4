"""Offline Chrome/GPU profile checks; never launch Chrome."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile_core', root / 'scripts/selkies-desktop.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)

source = (root / 'scripts/selkies-desktop.py').read_text()
assert core.CHROME_VERSION == '156.0.8078.47-1'
assert len(core.CHROME_SHA256) == 64
assert '--use-gl=egl' in source and '--ignore-gpu-blocklist' in source
assert '--renderer-process-limit=2' in source and '--process-per-site' in source
assert '--disable-background-networking' in source
assert 'google-chrome.desktop' in source
assert "PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'" in source
assert 'firefox' not in source.lower()
assert "mapping['__EGL_VENDOR_LIBRARY_FILENAMES']" in source
assert "SELKIES_VIDEO_STREAMING_MODE='true|locked'" in source
assert "SELKIES_USE_CPU='false|locked'" in source
assert "SELKIES_AUTO_GPU='nvidia'" in source
assert "SELKIES_RATE_CONTROL_MODE='cbr'" in source
assert 'pcfree-play' in core.INPUT_GUARD_JS and 'enterGamingMode()' in core.INPUT_GUARD_JS

with tempfile.TemporaryDirectory() as directory:
    home = Path(directory) / 'home'
    home.mkdir()
    account = type('Account', (), {'pw_uid': 1000, 'pw_gid': 1000})
    with patch.object(core, 'BASE', Path(directory) / 'state'), \
         patch.object(core, 'shortcut') as shortcut, \
         patch.object(core.pwd, 'getpwnam', return_value=account), \
         patch.object(core.os, 'chown'), \
         patch.object(core.subprocess, 'run') as run:
        profile = core.chrome_profile({'user': 'offline', 'home': str(home), 'env': {},
                                       'bin_dir': str(Path(directory) / 'bin')})
    wrapper = Path(directory) / 'bin/pcfree-chrome'
    text = wrapper.read_text()
    assert '--user-data-dir=' in text and '--use-gl=egl' in text
    assert '--renderer-process-limit=2' in text and '--disable-dev-shm-usage' in text
    assert profile.is_dir()
    helpers = home / '.config/xfce4/helpers.rc'
    assert 'WebBrowser=google-chrome' in helpers.read_text()
    assert shortcut.call_args.args[1] == 'Chrome'
    assert 'xdg-settings' in run.call_args.args[0]
    wrapper.unlink(missing_ok=True)
print('PASS: Chrome pinned, low-overhead flags, isolated profile, default browser, gesture CTA.')
