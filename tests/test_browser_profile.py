"""Offline browser/GPU profile checks; never launch Firefox."""
import importlib.util
from pathlib import Path
import tempfile
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile_core', root / 'scripts/selkies-desktop.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
with tempfile.TemporaryDirectory() as directory:
    with patch.object(core, 'BASE', Path(directory)), patch.object(core.pwd, 'getpwnam') as account, patch.object(core.os, 'chown'):
        account.return_value.pw_uid = 1000
        account.return_value.pw_gid = 1000
        profile = core.firefox_gpu_profile({'user': 'offline'})
        text = (profile / 'user.js').read_text()
        assert 'gfx.webrender.all' in text and 'webgl.force-enabled' in text
        assert 'sandbox' not in text
        assert profile.parent == Path(directory)
source = (root / 'scripts/selkies-desktop.py').read_text()
assert 'MOZ_X11_EGL=1' in source
assert "mapping['__EGL_VENDOR_LIBRARY_FILENAMES']" in source
assert "SELKIES_VIDEO_STREAMING_MODE='true|locked'" in source
assert "SELKIES_USE_CPU='false|locked'" in source
assert "SELKIES_AUTO_GPU='nvidia'" in source
assert "SELKIES_RATE_CONTROL_MODE='cbr'" in source
assert 'pcfree-play' in core.INPUT_GUARD_JS and 'enterGamingMode()' in core.INPUT_GUARD_JS
print('PASS: isolated Firefox profile, EGL/NVIDIA request, hardware gaming defaults, gesture-based CTA. FPS not measured.')
