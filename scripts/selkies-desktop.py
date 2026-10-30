"""Standalone Ubuntu 24.04/T4 desktop. Importing this module performs no setup.

Only bootstrap() installs/starts services. No notebook globals, Drive, keepalive,
driver installation, or automatic app windows. Logs stay on the ephemeral VM.
"""
import base64
import contextlib
import fcntl
import hashlib
import json
import os
import platform
import pwd
import re
import secrets
import shlex
import shutil
import subprocess
import tarfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path('/tmp/pcfree-selkies')
USER = 'pcfree-browser'
DISPLAY = ':98'
PORT = 8082
SELKIES_VERSION = '2.1.0'
SELKIES_DEB_VERSION = '2.1.0-1~ubuntu24.04'
SELKIES_DEB_SHA256 = 'cedba7a9d8bb4d07fd2b2139a518dc2c03452e0f0254c5bb088426623e2027f3'
SELKIES_URL = ('https://github.com/selkies-project/selkies/releases/download/'
               f'{SELKIES_VERSION}/selkies-{SELKIES_VERSION}-ubuntu24.04-amd64.deb')
CLOUDFLARED_VERSION = '2026.10.3'
CLOUDFLARED_SHA256 = '053b80b0a23031a038fdbf3c073f59f82b8f1f152aa67971d7383ffafc0dbab0'
CLOUDFLARED_URL = ('https://github.com/cloudflare/cloudflared/releases/download/'
                   f'{CLOUDFLARED_VERSION}/cloudflared-linux-amd64')
CHROME_VERSION = '156.0.8078.47-1'
CHROME_SHA256 = '6c92cd22e90c6e3e255d782991543fa2091db8614e8536a971a7433a5c4d7ac8'
CHROME_URL = ('https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/'
              f'google-chrome-stable_{CHROME_VERSION}_amd64.deb')
PACKAGES = ['xserver-xorg-core', 'xfce4-session', 'xfwm4', 'xfce4-panel',
            'xfdesktop4', 'xfce4-settings', 'thunar', 'xfce4-terminal',
            'dbus-x11', 'mesa-utils', 'vulkan-tools', 'x11-utils', 'x11-xserver-utils', 'xauth',
            'pulseaudio', 'pulseaudio-utils', 'ca-certificates', 'python3.12',
            'libgtk-3-0t64', 'libdbus-glib-1-2', 'libasound2t64', 'zenity', 'sudo']
OPTIONAL_PACKAGES = [
    'gstreamer1.0-libav', 'gstreamer1.0-plugins-good',
    'gstreamer1.0-plugins-bad', 'gstreamer1.0-plugins-ugly',
    'libavcodec-extra', 'libva2', 'libva-drm2', 'libva-x11-2', 'libvdpau1',
    'libopenal1', 'libsdl2-2.0-0',
    'xdg-utils', 'desktop-file-utils', 'shared-mime-info', 'fonts-liberation', 'wget',
]
TEST_PACKAGES = ['gcc-multilib', 'libc6-dev-i386', 'libx11-dev', 'libgl1-mesa-dev',
                 'libx11-dev:i386', 'libgl1-mesa-dev:i386']
I386_LIBRARIES = [
    'libgl1:i386', 'libglx0:i386', 'libglvnd0:i386', 'libegl1:i386',
    'libgles2:i386', 'libvulkan1:i386', 'libdrm2:i386', 'libgbm1:i386',
    'libx11-6:i386', 'libx11-xcb1:i386', 'libxext6:i386', 'libxrandr2:i386',
    'libxinerama1:i386', 'libxcursor1:i386', 'libxi6:i386', 'libxss1:i386',
    'libxtst6:i386', 'libxfixes3:i386', 'libxrender1:i386', 'libxcb1:i386',
    'libxcb-render0:i386', 'libxcb-shm0:i386', 'libxcb-dri3-0:i386',
    'libxkbcommon0:i386', 'libxkbcommon-x11-0:i386', 'libwayland-client0:i386',
    'libudev1:i386', 'libdbus-1-3:i386', 'libfontconfig1:i386',
    'libfreetype6:i386', 'libasound2t64:i386', 'libpulse0:i386',
    'libva2:i386', 'libva-drm2:i386', 'libva-x11-2:i386', 'libvdpau1:i386',
    'libopenal1:i386', 'libsdl2-2.0-0:i386', 'libstdc++6:i386',
]
AUDIO_SINK_ARGS = ['sink_name=output', 'rate=48000', 'channels=2',
                   'channel_map=front-left,front-right', 'format=s16le',
                   'sink_properties=device.description=PC-Free']


def audio_daemon_conf():
    """Stable 48 kHz pipeline: no flat volumes, cheap resampling, fewer wakeups.

    Without rtkit (Colab has none) realtime scheduling always fails; a negative
    nice applied before runuser does work. Larger fragments absorb NVENC bursts
    instead of producing xruns, which the client hears as crackle or freezes.
    """
    return '''# PC-Free: audio estable bajo carga de NVENC
default-sample-format = s16le
default-sample-rate = 48000
alternate-sample-rate = 48000
resample-method = speex-float-1
enable-lfe-remixing = no
flat-volumes = no
exit-idle-time = -1
high-priority = yes
nice-level = -10
realtime-scheduling = no
default-fragments = 4
default-fragment-size-msec = 40
'''


def private_json(path, value):
    """Atomic, root-private state; no secrets in session.json."""
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
    temporary.chmod(0o600)
    temporary.replace(path)


def capture(argv, env=None, timeout=60):
    return subprocess.check_output(argv, env=env, text=True, stderr=subprocess.STDOUT,
                                   timeout=timeout)


def logged(argv, name='install', env=None, timeout=600):
    path = BASE / (name + '.log')
    with path.open('a') as stream:
        result = subprocess.run(argv, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Falló {argv[0]}; consultar {path}.\n' + path.read_text()[-1800:])


def download(url, destination):
    """HTTPS official publisher URLs; publish only a completed download."""
    if urllib.parse.urlparse(url).scheme != 'https':
        raise ValueError('Se requiere HTTPS.')
    temporary = destination.with_suffix(destination.suffix + '.part')
    try:
        with urllib.request.urlopen(url, timeout=90) as response, temporary.open('wb') as out:
            if urllib.parse.urlparse(response.url).scheme != 'https':
                raise RuntimeError('Redirección insegura.')
            shutil.copyfileobj(response, out)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def require_sha256(path, expected):
    """Fail closed when the official digest does not match."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        Path(path).unlink(missing_ok=True)
        raise RuntimeError(f'SHA-256 inesperado para {Path(path).name}: {actual}; '
                           'descarga eliminada.')


@contextlib.contextmanager
def phase(name):
    start = time.monotonic()
    print(name + '…', flush=True)
    yield
    print(f'  {time.monotonic() - start:.1f} s', flush=True)


def wait_for(test, description, processes=(), timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError(f'{description}: proceso detenido; registros en {BASE}.')
        try:
            if test():
                return
        except (OSError, subprocess.SubprocessError, urllib.error.URLError):
            pass
        time.sleep(0.25)  # Readiness polling, never a session keepalive.
    raise RuntimeError(f'Tiempo agotado: {description}; registros en {BASE}.')


def pid_identity(pid):
    try:
        # comm can contain spaces: fields after the closing parenthesis start at #3.
        return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
    except (OSError, IndexError):
        return None


def already_running(session):
    entries = session.get('processes', {})
    return bool(entries) and all(pid_identity(item['pid']) == item['start']
                                 and item['start'] is not None for item in entries.values())


def preflight():
    if os.geteuid() != 0:
        raise RuntimeError('Requiere una VM Ubuntu administrada con permisos root.')
    release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines()
                   if '=' in line)
    if release.get('ID', '').strip('"') != 'ubuntu' or release.get('VERSION_ID', '').strip('"') != '24.04':
        raise RuntimeError('Esta receta requiere Ubuntu 24.04; no forzar otros paquetes.')
    if platform.machine() != 'x86_64':
        raise RuntimeError('Se requiere amd64.')
    if os.path.ismount('/content/drive'):
        raise RuntimeError('Desmontar Drive antes de preparar el escritorio.')
    if shutil.disk_usage('/tmp').free < 8 * 1024**3:
        raise RuntimeError('Se requieren al menos 8 GiB libres; los juegos necesitan más.')
    gpu_rows = [row.strip() for row in capture(
        ['nvidia-smi', '--query-gpu=name,driver_version,pci.bus_id', '--format=csv,noheader']
    ).splitlines() if row.strip()]
    # Un runtime puede exponer más de una T4. El escritorio necesita una GPU concreta;
    # se selecciona la primera T4 de nvidia-smi para el BusID de Xorg/Selkies.
    t4_rows = [row for row in gpu_rows if 'T4' in row.split(',', 1)[0]]
    if not t4_rows:
        raise RuntimeError('Se requiere al menos una GPU NVIDIA Tesla T4 visible por nvidia-smi.')
    name, driver, bus = (value.strip() for value in t4_rows[0].split(',', 2))
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', driver):
        raise RuntimeError('GPU/versión NVIDIA no compatible.')
    if len(t4_rows) > 1:
        print(f'Detectadas {len(t4_rows)} Tesla T4; Xorg/Selkies usará solo la primera: {name} ({bus}).', flush=True)
        print('Las GPU no se combinan: la segunda no duplica los FPS de un juego.', flush=True)
    if Path('/tmp/.X11-unix/X98').exists() or Path('/tmp/.X98-lock').exists():
        raise RuntimeError('Ya existe Xorg :98. No se reinicia ni se reinstala la sesión activa.')
    # Colab asigna vCPU/RAM al runtime; la receta no limita la afinidad de CPU.
    try:
        cpu_count = os.cpu_count() or 0
        mem_kib = next((int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()
                        if line.startswith('MemTotal:')), 0)
        print(f'Recursos visibles: {cpu_count} CPU lógicas | RAM {mem_kib / 1024**2:.1f} GiB', flush=True)
    except Exception as exc:
        print(f'Aviso: no se pudieron leer todos los recursos CPU/RAM: {exc}', flush=True)
    print(f'GPU: {name} | controlador del kernel: {driver}', flush=True)
    return driver, bus


def safe_apt_install(packages, validated_local_deb=None):
    """Do not permit apt dependency resolution to replace a GPU/kernel stack."""
    local_path = None
    local_filename = None
    if validated_local_deb is not None:
        # Only the exact official download explicitly passed by bootstrap. Never
        # permit arbitrary file: origins or infer trust from a package argument.
        local_path = Path(validated_local_deb)
        if (local_path != BASE / 'selkies.deb' or str(local_path) not in packages
                or local_path.is_symlink() or not local_path.is_file()):
            raise RuntimeError('DEB local no validado; operación cancelada.')
        metadata = dict(line.split(': ', 1) for line in
                        capture(['dpkg-deb', '-f', str(local_path)]).splitlines() if ': ' in line)
        if (metadata.get('Package') != 'selkies' or metadata.get('Version') != SELKIES_DEB_VERSION
                or metadata.get('Architecture') != 'amd64'):
            raise RuntimeError('Identidad del DEB Selkies inesperada; operación cancelada.')
        local_filename = f"selkies_{SELKIES_DEB_VERSION}_amd64.deb"
    plan = capture(['apt-get', '-s', 'install', '-y', '--no-install-recommends', *packages], timeout=120)
    for line in plan.splitlines():
        if line.startswith('Remv '):
            raise RuntimeError(f'APT propone eliminar {line[5:].strip()}; operación cancelada.')
        if line.startswith('Inst '):
            name = line.split()[1].split(':')[0]
            if 'nvidia' in name or name.startswith(('linux-image', 'linux-modules', 'linux-headers')):
                raise RuntimeError(f'APT propone cambiar {name}; no se modifica el controlador del host.')
    origins = capture(['apt-get', '--print-uris', '--download-only', 'install', '-y',
                       '--no-install-recommends', *packages], timeout=120)
    for uri, filename in re.findall(r"^'([^']*)'\s+(\S+)", origins, re.MULTILINE):
        parsed = urllib.parse.urlparse(uri)
        if local_path is not None:
            if (parsed.scheme == 'file' and not parsed.netloc and not parsed.query
                    and not parsed.fragment and urllib.parse.unquote(parsed.path) == str(local_path)):
                continue
            # Some APT versions omit the URI for an explicitly supplied local
            # archive. Match its metadata-derived cache filename, not any ''.
            if uri == '' and filename == local_filename:
                continue
        if not official_ubuntu_uri(uri):
            raise RuntimeError('APT propone un origen no permitido; operación cancelada.')
    logged(['apt-get', 'install', '-y', '--no-install-recommends', *packages],
           env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'})


def safe_optional_install(packages, label):
    """Install optional extras without aborting the desktop on APT conflicts."""
    try:
        safe_apt_install(packages)
        print(f'{label}: instalados en grupo.', flush=True)
        return
    except RuntimeError as exc:
        print(f'Aviso: {label} se omite en grupo ({exc}); se intentará por paquete.', flush=True)
    for package in packages:
        try:
            safe_apt_install([package])
            print(f'  [OK] {package}', flush=True)
        except RuntimeError as exc:
            print(f'  [SKIP] {package}: {exc}', flush=True)


def install_compat_libraries():
    """32-bit runtime libs for native games and Wine/Proton."""
    logged(['dpkg', '--add-architecture', 'i386'], 'i386-arch', timeout=120)
    logged(['apt-get', 'update', '-qq'], 'i386-update', timeout=240)
    safe_optional_install(I386_LIBRARIES, 'Bibliotecas 32 bits')
    safe_optional_install(TEST_PACKAGES, 'Herramientas de prueba 32/64 bits')


def install_optional_packages():
    safe_optional_install(OPTIONAL_PACKAGES, 'Códecs, fuentes y utilidades del navegador')


def matching_version(madison, driver):
    for line in madison.splitlines():
        columns = [part.strip() for part in line.split('|')]
        if len(columns) >= 3:
            version = columns[1]
            upstream = version.split(':')[-1].split('-')[0]
            if upstream == driver:
                return version
    raise RuntimeError(f'Los repositorios oficiales no ofrecen bibliotecas NVIDIA {driver} exactas. '
                       'Detenerse: no instalar otro controlador ni sustituir el del kernel.')


def official_ubuntu_uri(uri):
    """Ubuntu archives or NVIDIA's official CUDA APT repo for this exact OS/arch.

    APT must already have authenticated the repository metadata; never add keys,
    PPAs or trusted=yes, and never use a different driver version as fallback.
    """
    parsed = urllib.parse.urlparse(uri)
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        return False
    ubuntu = (parsed.scheme in ('http', 'https') and
              (parsed.hostname in ('archive.ubuntu.com', 'security.ubuntu.com', 'ports.ubuntu.com')
               or (parsed.hostname or '').endswith('.archive.ubuntu.com')))
    path = urllib.parse.unquote(parsed.path)
    nvidia = (parsed.scheme == 'https' and parsed.port in (None, 443) and
              parsed.hostname == 'developer.download.nvidia.com' and
              path.startswith('/compute/cuda/repos/ubuntu2404/x86_64/') and
              '..' not in path.split('/'))
    return ubuntu or nvidia


def graphics(driver):
    branch = driver.split('.')[0]
    packages = [f'{name}-{branch}' for name in ('libnvidia-gl', 'libnvidia-gpucomp',
                'libnvidia-cfg1', 'libnvidia-encode', 'libnvidia-compute', 'xserver-xorg-video-nvidia')]
    destination = BASE / 'nvidia'; destination.mkdir(exist_ok=True)
    # Resolve ALL versions and origins before extraction. Never install these debs.
    selected = []
    for package in packages:
        version = matching_version(capture(['apt-cache', 'madison', package]), driver)
        spec = package + '=' + version
        origins = capture(['apt-get', '--print-uris', 'download', spec])
        uris = re.findall(r"^'([^']+)'", origins, re.MULTILINE)
        if not uris or not all(official_ubuntu_uri(uri) for uri in uris):
            raise RuntimeError(f'{package}: origen no permitido (Ubuntu/NVIDIA oficial); operación cancelada.')
        selected.append(spec)
    for spec in selected:
        with (BASE / 'nvidia-download.log').open('a') as log:
            subprocess.run(['apt-get', 'download', spec], cwd=destination,
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=180)
    root = destination / 'root'
    for deb in destination.glob('*.deb'):
        # dpkg-deb extraction executes no maintainer scripts and installs no driver.
        logged(['dpkg-deb', '-x', str(deb), str(root)], 'nvidia-extract')
    libraries = sorted({str(path.parent) for path in root.rglob('*.so*') if path.is_file()})
    if not libraries or not list(root.rglob('nvidia_drv.so')):
        raise RuntimeError('Paquetes NVIDIA incompletos; revisar nvidia-download.log.')
    # `nvidia-smi --query-gpu=driver_version` imprime una línea por GPU.
    # En un runtime multi-GPU, comparar todo el texto con una sola versión causa un falso
    # positivo aunque el controlador siga igual: las dos líneas repiten la versión.
    # Valida de nuevo cada T4 visible sin instalar ni cambiar el controlador del kernel.
    actual_output = capture([
        'nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'
    ]).strip()
    actual_t4_versions = []
    for line in actual_output.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(',', 1)]
        if len(parts) == 2 and 'T4' in parts[0]:
            actual_t4_versions.append(parts[1])
    if not actual_t4_versions or any(version != driver for version in actual_t4_versions):
        observed = ', '.join(actual_t4_versions) if actual_t4_versions else 'ninguna T4 visible'
        raise RuntimeError(
            f'La versión del controlador NVIDIA no coincide: esperada {driver}; '
            f'detectada en T4: {observed}. No se instaló ningún controlador del kernel.'
        )
    print(
        f'Controlador verificado en {len(actual_t4_versions)} T4(s): {driver}; '
        'las bibliotecas de la cuenta permanecen aisladas del kernel.', flush=True
    )
    return root, ':'.join(libraries)


def prepare_user(root, libraries):
    try:
        account = pwd.getpwnam(USER)
    except KeyError:
        logged(['useradd', '--create-home', '--home-dir', str(BASE / 'home'), '--shell', '/bin/bash', USER])
        account = pwd.getpwnam(USER)
    if account.pw_uid == 0:
        raise RuntimeError('La cuenta de escritorio no puede ser root.')
    import grp
    groups = []
    for name in ('video', 'render'):
        try:
            grp.getgrnam(name)
            groups.append(name)
        except KeyError:
            pass
    if groups:
        logged(['usermod', '-aG', ','.join(groups), USER])
    home = Path(account.pw_dir)
    runtime = BASE / 'runtime'
    for directory in (home, runtime, home / 'Desktop', home / 'Downloads'):
        directory.mkdir(parents=True, exist_ok=True)
        os.chown(directory, account.pw_uid, account.pw_gid)
    runtime.chmod(0o700)
    authority = BASE / '.Xauthority'
    authority.touch(mode=0o600); authority.chmod(0o600)
    logged(['xauth', '-f', str(authority), 'add', DISPLAY, 'MIT-MAGIC-COOKIE-1', secrets.token_hex(16)])
    os.chown(authority, account.pw_uid, account.pw_gid)
    pulse_config = home / '.config/pulse'
    pulse_config.mkdir(parents=True, exist_ok=True)
    cookie = pulse_config / 'cookie'
    if not cookie.exists():
        with cookie.open('xb') as stream:
            stream.write(secrets.token_bytes(256))
    cookie.chmod(0o600)
    daemon_conf = pulse_config / 'daemon.conf'
    daemon_conf.write_text(audio_daemon_conf())
    daemon_conf.chmod(0o644)
    for item in (home / '.config', pulse_config, cookie, daemon_conf):
        os.chown(item, account.pw_uid, account.pw_gid)
    env = {**os.environ, 'DISPLAY': DISPLAY, 'XAUTHORITY': str(authority),
           'HOME': str(home), 'USER': USER, 'LOGNAME': USER, 'XDG_RUNTIME_DIR': str(runtime),
           'PULSE_SERVER': f'unix:{runtime}/pulse/native', 'PULSE_COOKIE': str(cookie), 'LD_LIBRARY_PATH': libraries,
           '__GLX_VENDOR_LIBRARY_NAME': 'nvidia', 'SELKIES_INTERPOSER': '/usr/$LIB/selkies_input_interposer.so'}
    for key in ('LD_PRELOAD', 'DBUS_SESSION_BUS_ADDRESS', 'SESSION_MANAGER',
                'SELKIES_BASIC_AUTH_USER', 'SELKIES_BASIC_AUTH_PASSWORD', 'PASSWORD', 'PASSWD'):
        env.pop(key, None)
    env['DBUS_SESSION_BUS_ADDRESS'] = f'unix:path={runtime}/bus'
    # Persist only an explicit environment allowlist; never inherited Colab tokens.
    keep = ('DISPLAY', 'XAUTHORITY', 'HOME', 'USER', 'LOGNAME', 'XDG_RUNTIME_DIR',
            'PULSE_SERVER', 'PULSE_COOKIE', 'LD_LIBRARY_PATH', '__GLX_VENDOR_LIBRARY_NAME',
            'SELKIES_INTERPOSER', 'DBUS_SESSION_BUS_ADDRESS')
    session = dict(user=USER, home=str(home), runtime=str(runtime), display=DISPLAY,
                   xauthority=str(authority), gpu_root=str(root),
                   env={key: env[key] for key in keep}, run_launcher='/usr/local/bin/pcfree-run')
    return session, env


def vulkan_icd(root):
    """Create a private NVIDIA ICD manifest without changing system-wide Vulkan config.

    In this runtime, a direct probe found the NVIDIA EGL library exposed the T4,
    while the GLX library path failed ICD entry-point loading. Prefer EGL when present;
    keep the driver-provided api_version and all other manifest fields unchanged.
    """
    candidates = list(root.rglob('nvidia_icd.json'))
    if len(candidates) != 1:
        raise RuntimeError('ICD Vulkan NVIDIA oficial no encontrado o ambiguo.')
    document = json.loads(candidates[0].read_text())
    egl_library = root / 'usr/lib/x86_64-linux-gnu/libEGL_nvidia.so.0'
    glx_library = root / 'usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0'
    library = egl_library if egl_library.is_file() else glx_library
    if not library.is_file() or not document.get('ICD', {}).get('api_version'):
        raise RuntimeError('ICD/biblioteca NVIDIA incompletos: EGL y GLX no encontrados.')
    document['ICD']['library_path'] = str(library)
    destination = BASE / 'nvidia-vulkan64.json'
    destination.write_text(json.dumps(document, indent=2) + '\n')
    destination.chmod(0o644)  # Not secret; the unprivileged Vulkan loader reads it.
    return str(destination)

SHM_PERMS_SOURCE = r'''#define _GNU_SOURCE
#include <dlfcn.h>
#include <sys/ipc.h>
#include <sys/shm.h>
/* Colab containers: Xorg cannot read SO_PEERCRED of the capture client, so MIT-SHM
   only attaches world-accessible segments (else BadAccess, X11 error 10). */
int shmget(key_t key, size_t size, int flags) {
    static int (*real)(key_t, size_t, int);
    if (!real) real = (int (*)(key_t, size_t, int))dlsym(RTLD_NEXT, "shmget");
    if (flags & IPC_CREAT) flags |= 0666;
    return real(key, size, flags);
}
'''


def shm_perms_library():
    """Build shm-perms.so on every fresh VM; never trust a leftover file."""
    library = BASE / 'shm-perms.so'
    source = BASE / 'shm-perms.c'
    source.write_text(SHM_PERMS_SOURCE)
    if not shutil.which('gcc'):
        safe_apt_install(['gcc', 'libc6-dev'])
    library.unlink(missing_ok=True)
    logged(['gcc', '-shared', '-fPIC', '-O2', '-o', str(library), str(source), '-ldl'])
    library.chmod(0o755)
    if 'shmget' not in capture(['nm', '-D', '--defined-only', str(library)]):
        raise RuntimeError('shm-perms.so no exporta shmget; XShm no quedaría corregido.')
    return str(library)


def as_user(argv):
    return ['runuser', '-u', USER, '--', *argv]


def spawn(argv, name, env, processes, user=True, nice=None):
    command = as_user(argv) if user else argv
    if nice is not None:
        # Lower the nice value as root before runuser drops privileges: setuid
        # keeps it, while the desktop user could not raise its own priority.
        command = ['nice', '-n', str(nice), *command]
    with (BASE / (name + '.log')).open('a') as log:
        process = subprocess.Popen(command, env=env,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    processes[name] = process
    return process


def launcher_source(session):
    # $LIB is expanded by the ELF loader per-process architecture, not by a shell.
    # This handles 32-bit children of 64-bit Steam/Wine too, unlike probing argv[0].
    return '''#!/usr/bin/python3.12
import json, os, pwd, sys
if len(sys.argv) < 2:
    raise SystemExit('Uso: pcfree-run programa [argumentos]')
settings = SETTINGS
account = pwd.getpwnam(settings['user'])
if os.geteuid() not in (0, account.pw_uid):
    raise SystemExit('Cuenta de escritorio requerido.')
env = dict(os.environ)
env.update(settings['env'])
env.pop('LD_PRELOAD', None)
# Ubuntu amd64 glibc $LIB: lib/x86_64-linux-gnu; i386: lib/i386-linux-gnu.
if os.path.exists('/usr/lib/x86_64-linux-gnu/selkies_input_interposer.so'):
    env['LD_PRELOAD'] = '/usr/$LIB/selkies_input_interposer.so'
    fake = '/tmp/pcfree-selkies/fake-udev/'
    if all(os.path.exists(fake+'lib/'+arch+'/libudev.so.1')
           for arch in ('x86_64-linux-gnu', 'i386-linux-gnu')):
        env['LD_PRELOAD'] = fake+'$LIB/libudev.so.1:'+env['LD_PRELOAD']
        env.pop('SDL_JOYSTICK_DISABLE_UDEV', None)
        env.pop('SDL_JOYSTICK_DEVICE', None)
    else:
        env['SDL_JOYSTICK_DISABLE_UDEV'] = '1'
        env['SDL_JOYSTICK_DEVICE'] = ':'.join('/dev/input/event'+str(i) for i in range(1000,1004))
else:
    print('Aviso: interposer no encontrado; mandos no preparados.', file=sys.stderr)
if os.geteuid() == 0:
    os.initgroups(account.pw_name, account.pw_gid)
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
os.execvpe(sys.argv[1], sys.argv[1:], env)
'''.replace('SETTINGS', repr(session))


def shortcut(session, filename, name, command, icon, terminal=False):
    path = Path(session['home']) / 'Desktop' / (filename + '.desktop')
    path.write_text('[Desktop Entry]\nVersion=1.0\nType=Application\n'
                    f'Name={name}\nExec={command}\nIcon={icon}\nTerminal={str(terminal).lower()}\n')
    path.chmod(0o755)
    account = pwd.getpwnam(session['user']); os.chown(path, account.pw_uid, account.pw_gid)


def desktop_files(session):
    path = Path(session['home']) / '.config/xfce4/xfconf/xfce-perchannel-xml'
    path.mkdir(parents=True, exist_ok=True)
    (path / 'xfwm4.xml').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfwm4" version="1.0"><property name="general" type="empty">
<property name="use_compositing" type="bool" value="false"/>
</property></channel>
''')
    account = pwd.getpwnam(USER)
    config_home = Path(session['home']) / '.config'
    for item in [config_home, *config_home.rglob('*')]:
        os.chown(item, account.pw_uid, account.pw_gid)
    runner = Path(session['run_launcher']); runner.write_text(launcher_source(session)); runner.chmod(0o755)
    inputs = Path('/dev/input')
    if not inputs.exists():
        inputs.mkdir(mode=0o1777)
        inputs.chmod(0o1777)
    shortcut(session, 'Terminal', 'Terminal', 'pcfree-run xfce4-terminal', 'utilities-terminal')
    shortcut(session, 'Archivos', 'Archivos', 'pcfree-run thunar', 'system-file-manager')
    shortcut(session, 'Descargas', 'Descargas', 'pcfree-run thunar ' + session['home'] + '/Downloads', 'folder-download')
    package_installer(session)


def package_installer(session):
    """Interactive, small allowlist: no unrestricted passwordless sudo/apt."""
    allowed = ['mousepad', 'gimp', 'vlc', 'p7zip-full', 'unzip', 'file-roller', 'htop']
    helper = Path('/usr/local/sbin/pcfree-install-package')
    # Root-owned script; official origins and safe dependency plan.
    helper.write_text('''#!/usr/bin/python3.12
import os, re, subprocess, sys, urllib.parse
def official_ubuntu_uri(uri):
    parsed = urllib.parse.urlparse(uri)
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        return False
    host = parsed.hostname or ''
    ubuntu = parsed.scheme in ('http', 'https') and (
        host in ('archive.ubuntu.com','security.ubuntu.com','ports.ubuntu.com')
        or host.endswith('.archive.ubuntu.com'))
    path = urllib.parse.unquote(parsed.path)
    nvidia = (parsed.scheme == 'https' and parsed.port in (None, 443)
        and host == 'developer.download.nvidia.com'
        and path.startswith('/compute/cuda/repos/ubuntu2404/x86_64/')
        and '..' not in path.split('/'))
    return ubuntu or nvidia
ALLOWED = ALLOWLIST
if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in ALLOWED:
    raise SystemExit('Seleccionar un paquete permitido desde el icono Instalador.')
plan = subprocess.check_output(['apt-get','-s','install','-y','--no-install-recommends',sys.argv[1]], text=True)
for line in plan.splitlines():
    if line.startswith('Remv ') or (line.startswith('Inst ') and
       ('nvidia' in line.split()[1] or line.split()[1].startswith(('linux-image','linux-modules','linux-headers')))):
        raise SystemExit('Operación insegura: cambios del controlador/kernel o eliminaciones.')
uris = subprocess.check_output(['apt-get','--print-uris','--download-only','install','-y','--no-install-recommends',sys.argv[1]], text=True)
for uri in re.findall(r"^'([^']+)'", uris, re.MULTILINE):
    if not official_ubuntu_uri(uri):
        raise SystemExit('Origen no permitido: solamente Ubuntu o NVIDIA CUDA oficial Ubuntu24.04 amd64.')
subprocess.run(['apt-get','install','-y','--no-install-recommends',sys.argv[1]], check=True,
               env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'})
'''.replace('ALLOWLIST', repr(allowed)))
    helper.chmod(0o755)
    rule = Path('/etc/sudoers.d/pcfree-packages')
    rule.write_text(f'{USER} ALL=(root) NOPASSWD: /usr/local/sbin/pcfree-install-package *\n')
    rule.chmod(0o440)
    logged(['visudo', '-cf', str(rule)])
    gui = Path('/usr/local/bin/pcfree-install')
    gui.write_text('#!/bin/sh\npackage=$(zenity --list --title="Paquetes Ubuntu" --column="Paquete" '
                   + ' '.join(shlex.quote(item) for item in allowed) + ') || exit\n'
                   + 'sudo -n /usr/local/sbin/pcfree-install-package "$package"\nread -r _\n')
    gui.chmod(0o755)
    shortcut(session, 'Instalador', 'Instalador de paquetes Ubuntu', 'pcfree-run pcfree-install', 'system-software-install', True)


def install_chrome():
    """Install the pinned official Chrome .deb after validating the APT plan."""
    deb = BASE / 'chrome.deb'
    download(CHROME_URL, deb)
    require_sha256(deb, CHROME_SHA256)
    plan = capture(['apt-get', '-s', 'install', '-y', '--no-install-recommends', str(deb)],
                   timeout=180)
    for line in plan.splitlines():
        if line.startswith('Remv '):
            raise RuntimeError('APT propone eliminar paquetes para Chrome; cancelado.')
        if line.startswith('Inst '):
            name = line.split()[1].split(':', 1)[0]
            if 'nvidia' in name or name.startswith(('linux-image', 'linux-modules',
                                                    'linux-headers', 'linux-generic')):
                raise RuntimeError(f'Chrome intentaría cambiar {name}; cancelado.')
    origins = capture(['apt-get', '--print-uris', '--download-only', 'install', '-y',
                       '--no-install-recommends', str(deb)], timeout=180)
    for uri, filename in re.findall(r"^'([^']*)'\s+(\S+)", origins, re.MULTILINE):
        if uri.startswith('file:'):
            local = Path(urllib.parse.unquote(urllib.parse.urlparse(uri).path)).resolve()
            if local == deb.resolve():
                continue
        if uri == '' and filename.startswith('google-chrome-stable_'):
            continue
        if not official_ubuntu_uri(uri):
            raise RuntimeError(f'Origen no oficial para Chrome: {uri}')
    logged(['apt-get', 'install', '-y', '--no-install-recommends', str(deb)],
           'chrome-install', env={**os.environ, 'DEBIAN_FRONTEND': 'noninteractive'},
           timeout=900)
    deb.unlink(missing_ok=True)
    version = capture(['google-chrome', '--version'], timeout=30)
    if 'Google Chrome' not in version:
        raise RuntimeError('Google Chrome no se instaló correctamente.')
    print(f'Chrome: {version.strip()}', flush=True)


def chrome_profile(session):
    """Private profile, low-overhead flags and default browser registration."""
    BASE.mkdir(mode=0o755, exist_ok=True)
    profile = BASE / 'chrome-profile'
    profile.mkdir(mode=0o700, exist_ok=True)
    account = pwd.getpwnam(session['user'])
    os.chown(profile, account.pw_uid, account.pw_gid)
    flags = [
        f'--user-data-dir={profile}',
        '--no-first-run', '--no-default-browser-check',
        '--disable-background-networking', '--disable-component-update',
        '--disable-sync', '--disable-extensions', '--disable-default-apps',
        '--disable-breakpad', '--disable-hang-monitor', '--disable-notifications',
        '--disable-features=Translate,MediaRouter,OptimizationHints',
        '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
        '--disable-backgrounding-occluded-windows', '--disable-dev-shm-usage',
        '--renderer-process-limit=2', '--process-per-site',
        '--disk-cache-size=134217728', '--media-cache-size=33554432',
        '--use-gl=egl', '--ignore-gpu-blocklist', '--ozone-platform=x11',
    ]
    wrapper = Path(session.get('bin_dir', '/usr/local/bin')) / 'pcfree-chrome'
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text('#!/bin/sh\nexec /usr/local/bin/pcfree-run /usr/bin/google-chrome '
                       + ' '.join(shlex.quote(flag) for flag in flags) + ' "$@"\n')
    wrapper.chmod(0o755)
    shortcut(session, 'Chrome', 'Google Chrome', str(wrapper) + ' %u', 'google-chrome')
    home = Path(session['home'])
    helpers = home / '.config' / 'xfce4' / 'helpers.rc'
    helpers.parent.mkdir(parents=True, exist_ok=True)
    lines = helpers.read_text().splitlines() if helpers.exists() else []
    lines = [line for line in lines if not line.startswith('WebBrowser=')]
    lines.append('WebBrowser=google-chrome')
    helpers.write_text('\n'.join(lines) + '\n')
    os.chown(helpers, account.pw_uid, account.pw_gid)
    env = dict(session['env'], XDG_CURRENT_DESKTOP='XFCE',
               PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')
    subprocess.run(as_user(['xdg-settings', 'set', 'default-web-browser',
                            'google-chrome.desktop']), env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
    (BASE / 'chrome-status.txt').write_text('listo\n')
    print('Chrome listo: perfil aislado y navegador predeterminado.', flush=True)
    return profile


def show_access():
    access = json.loads((BASE / 'access.json').read_text())
    print('\nAcceso privado — no guardar estas salidas en GitHub:', flush=True)
    print('URL:', access['url'], '\nCuenta:', access['username'], '\nContraseña:', access['password'], flush=True)
    state = BASE / 'session.json'
    settings = json.loads(state.read_text()).get('settings', {}) if state.exists() else {}
    fps, kbps = settings.get('framerate', 30), settings.get('bitrate', 2000)
    resolution = settings.get('resolution', '960x540')
    encoder = settings.get('encoder', 'h264enc')
    cpu_encode = str(settings.get('use_cpu', False)).lower()
    queue_size = settings.get('backpressure_queue_size', 120)
    congestion = 'activa' if settings.get('congestion_control') else 'desactivada'
    print(f'{resolution} · {encoder} · use-cpu={cpu_encode} · cola={queue_size} · {fps} FPS · {kbps} kbps CBR · congestión {congestion}; NVENC se confirma en TX · Diagnóstico.')
    chrome = 'instalado, perfil aislado' if settings.get('chrome') else 'desactivado'
    print(f'Registros: {BASE} | Chrome: {chrome}, sin abrir ventanas.')


def auth_ready(username, password):
    url = f'http://127.0.0.1:{PORT}/'
    try:
        urllib.request.urlopen(url, timeout=2).close()
        raise RuntimeError('Selkies sirve contenido sin autenticación; no publicar túnel.')
    except urllib.error.HTTPError as error:
        if error.code != 401:
            return False
    header = base64.b64encode(f'{username}:{password}'.encode()).decode()
    request = urllib.request.Request(url, headers={'Authorization': 'Basic ' + header})
    with urllib.request.urlopen(request, timeout=2) as response:
        return response.status == 200


INPUT_GUARD_JS = r'''(() => {
  // Only cancel browser defaults over the stream, never stop input forwarding.
  // OS-level Android BACK and reserved system shortcuts cannot be intercepted.
  const streamTarget = target => target instanceof Element &&
    !!target.closest('#overlayInput, #videoCanvas, #videoWorkerCanvas, #videoStream, #stream');
  document.addEventListener('mousedown', event => {
    if (event.button === 2 && streamTarget(event.target)) event.preventDefault();
  }, {capture: true, passive: false});
  document.addEventListener('contextmenu', event => {
    if (streamTarget(event.target)) event.preventDefault();
  }, {capture: true, passive: false});
  window.pcfreeInputGuard = {version: 1, osBackCapture: false};
  const addGamingButton = () => {
    const nativeButton = document.querySelector('button.gaming-mode-button');
    if (!nativeButton || document.getElementById('pcfree-play')) return !!nativeButton;
    const button = document.createElement('button');
    button.id = 'pcfree-play'; button.type = 'button'; button.textContent = 'Jugar';
    button.title = 'Pantalla completa y captura de controles; requiere permisos del navegador';
    button.style.cssText = 'position:fixed;bottom:12px;left:12px;z-index:10000;padding:8px 16px;background:#166534;color:white;border:1px solid #86efac;border-radius:8px;cursor:pointer';
    button.addEventListener('click', () => {
      // Use the upstream handler within this real user-activated click.
      if (typeof window.webrtcInput?.enterGamingMode === 'function') window.webrtcInput.enterGamingMode();
      else document.querySelector('button.gaming-mode-button')?.click();
    });
    const visibility = () => { button.hidden = !!document.fullscreenElement; };
    document.addEventListener('fullscreenchange', visibility);
    document.body.appendChild(button); visibility();
    return true;
  };
  const start = () => {
    if (addGamingButton()) return;
    // Only the dashboard needs the CTA. Input-only iframe stays lightweight.
    if (window.self !== window.top) return;
    const observer = new MutationObserver(() => { if (addGamingButton()) observer.disconnect(); });
    observer.observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
'''


def prepare_web_client(source=None):
    """Private static copy; keep upstream bundles and native Gaming Mode intact."""
    source = Path(source or '/opt/selkies/lib/python3.12/site-packages/selkies/selkies_web')
    if not (source / 'index.html').is_file() or not (source / 'assets').is_dir():
        raise RuntimeError('Cambió la estructura del cliente Selkies; revisar paquete antes de aplicar controles.')
    target = BASE / 'web-client'
    shutil.copytree(source, target, dirs_exist_ok=True)
    marker = '<script src="./pcfree-input-guard.js"></script>'
    for index in target.glob('*.html'):
        html = index.read_text()
        if '</head>' not in html:
            raise RuntimeError('Cliente web sin cabecera reconocible; no modificar bundles.')
        if marker not in html:
            index.write_text(html.replace('</head>', marker + '\n</head>', 1))
    (target / 'pcfree-input-guard.js').write_text(INPUT_GUARD_JS)
    return str(target)


def verify_pixelflux(python):
    """Selkies 2.1 bundles pixelflux 2.2.1; never replace it with an older wheel."""
    result = capture([
        str(python), '-c',
        'import importlib.metadata as m, pixelflux; '
        'print(m.version("pixelflux")); print(pixelflux.__file__)'
    ], timeout=60)
    lines = [line.strip() for line in result.splitlines() if line.strip()]
    version = lines[0] if lines else ''
    module = lines[1] if len(lines) > 1 else ''
    try:
        parts = tuple(int(part) for part in version.split('.')[:3])
    except ValueError:
        raise RuntimeError(f'Versión de pixelflux ilegible: {version!r}')
    if parts < (2, 2, 1):
        raise RuntimeError(f'Pixelflux {version} es anterior a 2.2.1; no se inicia.')
    if '/opt/selkies/lib/python3.12/site-packages/pixelflux' not in module:
        raise RuntimeError(f'Pixelflux no se importa desde /opt/selkies: {module}')
    (BASE / 'pixelflux-version.log').write_text(f'{version}\n{module}\n')
    print(f'Pixelflux {version} verificado: {module}', flush=True)


def bootstrap(chrome=True, framerate=60, bitrate=3000, width=960, height=540,
              backpressure_queue_size=120, congestion_control=False):
    if (
        not isinstance(framerate, int) or not 1 <= framerate <= 60
        or not isinstance(bitrate, int) or not 500 <= bitrate <= 20000
        or not isinstance(width, int) or not 320 <= width <= 3840
        or not isinstance(height, int) or not 240 <= height <= 2160
        or not isinstance(backpressure_queue_size, int) or not 1 <= backpressure_queue_size <= 100000
        or not isinstance(congestion_control, bool)
    ):
        raise ValueError('FPS: 1–60; bitrate: 500–20000 kbps; resolución: 320–3840 × 240–2160; '
                         'cola: 1–100000; congestion_control: booleano.')
    BASE.mkdir(mode=0o755, exist_ok=True)
    with (BASE / 'bootstrap.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Otra preparación está en curso; no ejecutar dos veces.')
        state = BASE / 'session.json'
        if state.exists():
            session = json.loads(state.read_text())
            if already_running(session):
                print('Sesión ya activa; no se reinicia ni se reinstala.')
                show_access()
                return session
            raise RuntimeError('Estado previo incompleto/detenido. Revisar registros; no reiniciar automáticamente. Usar VM nueva.')
        started = time.monotonic()
        with phase('Comprobaciones'):
            driver, bus = preflight()
        with phase('Paquetes mínimos y Selkies oficial'):
            logged(['apt-get', 'update', '-qq'], timeout=240)
            safe_apt_install(PACKAGES)
            install_optional_packages()
            install_compat_libraries()
            chrome_ok = False
            if chrome:
                try:
                    install_chrome()
                    chrome_ok = True
                except Exception as exc:
                    print(f'AVISO: Chrome no se instaló: {exc}', flush=True)
            deb = BASE / 'selkies.deb'; download(SELKIES_URL, deb)
            require_sha256(deb, SELKIES_DEB_SHA256)
            safe_apt_install([str(deb)], validated_local_deb=deb)
            deb.unlink(missing_ok=True)
            # Only fix the private package venv, NEVER /usr/bin/python3.
            python = Path('/opt/selkies/bin/python3')
            if not python.is_symlink():
                raise RuntimeError('Python privado Selkies inesperado; no modificar Python del sistema.')
            python.unlink(); python.symlink_to('/usr/bin/python3.12')
            verify_pixelflux(python)
            capture(['/opt/selkies/bin/selkies', '--help'])
            web_root = prepare_web_client()
            shm_perms = shm_perms_library()
            tunnel = BASE / 'cloudflared'; download(CLOUDFLARED_URL, tunnel)
            require_sha256(tunnel, CLOUDFLARED_SHA256)
            tunnel.chmod(0o755)
            logged(['apt-get', 'clean'], 'apt-clean', timeout=120)
        with phase('Bibliotecas 3D exactas, aisladas del kernel'):
            root, libraries = graphics(driver)
            session, env = prepare_user(root, libraries)
            for deb in (BASE / 'nvidia').glob('*.deb'):
                deb.unlink(missing_ok=True)
            icd = vulkan_icd(root)
            for key in ('VK_DRIVER_FILES', 'VK_ICD_FILENAMES'):
                env[key] = icd
                session['env'][key] = icd
            egl = BASE / 'nvidia-egl.json'
            egl_library = next(root.rglob('libEGL_nvidia.so.0'), None)
            if egl_library is None:
                raise RuntimeError('Falta EGL NVIDIA para el navegador; no usar renderizado software silencioso.')
            egl.write_text(json.dumps({'file_format_version': '1.0.0',
                                      'ICD': {'library_path': str(egl_library)}}))
            for mapping in (env, session['env']):
                mapping['__EGL_VENDOR_LIBRARY_FILENAMES'] = str(egl)
            session['driver_version'] = driver
            session['settings'] = {
                'framerate': framerate, 'bitrate': bitrate, 'chrome': chrome_ok,
                'width': width, 'height': height, 'resolution': f'{width}x{height}',
                'encoder': 'h264enc', 'use_cpu': False,
                'backpressure_queue_size': backpressure_queue_size,
                'rate_control_mode': 'cbr', 'enable_resize': True,
                'congestion_control': congestion_control,
            }
            desktop_files(session)
            if chrome_ok:
                try:
                    chrome_profile(session)
                except Exception as exc:
                    session['settings']['chrome'] = False
                    print(f'AVISO: perfil de Chrome no creado: {exc}', flush=True)
        # Mark setup BEFORE launching, so failures never cause a destructive rerun.
        session['processes'] = {}
        private_json(state, session)
        processes = {}
        with phase('Xorg NVIDIA, XFCE y audio'):
            parts = bus.split(':'); device, function = parts[-1].split('.')
            busid = f'PCI:{int(parts[-2],16)}:{int(device,16)}:{int(function,16)}'
            config = BASE / 'xorg.conf'
            config.write_text('''Section "ServerFlags"
 Option "AutoAddDevices" "false"
 Option "AutoAddGPU" "false"
EndSection
Section "Device"
 Identifier "T4"
 Driver "nvidia"
 BusID "BUSID"
 Option "AllowEmptyInitialConfiguration" "true"
EndSection
Section "Screen"
 Identifier "GPU-Screen"
 Device "T4"
 DefaultDepth 24
 SubSection "Display"
  Depth 24
  Virtual MAX_WIDTH MAX_HEIGHT
 EndSubSection
EndSection
'''.replace('BUSID', busid).replace('MAX_WIDTH', str(max(width, 1920))).replace('MAX_HEIGHT', str(max(height, 1080))))
            module = next(root.rglob('nvidia_drv.so')).parent.parent
            xorg = spawn(['/usr/lib/xorg/Xorg', DISPLAY, '-config', str(config), '-modulepath',
                          f'{module},/usr/lib/xorg/modules', '-logfile', str(BASE / 'Xorg.log'),
                          '-nolisten', 'tcp', '-noreset', '-novtswitch', '-sharevts', '-auth',
                          session['xauthority']], 'xorg', env, processes, user=False)
            def display_ready():
                return subprocess.run(as_user(['xdpyinfo']), env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, timeout=3).returncode == 0
            wait_for(display_ready, 'Xorg', [xorg])
            renderer = capture(as_user(['glxinfo', '-B']), env=env)
            (BASE / 'opengl.log').write_text(renderer)
            if 'NVIDIA' not in renderer or 'T4' not in renderer:
                raise RuntimeError('OpenGL T4 no confirmado; revisar Xorg.log.')
            # Vulkan is optional for desktop availability: a Vulkan loader/WSI failure must not
            # prevent the known-good NVIDIA OpenGL + Steam + Selkies path from starting.
            try:
                vulkan = capture(as_user(['vulkaninfo', '--summary']), env=env, timeout=30)
                vulkan_rc = 0
            except Exception as exc:
                vulkan = f'vulkaninfo no pudo completar: {type(exc).__name__}: {exc}\n'
                vulkan_rc = 1
            (BASE / 'vulkan.log').write_text(vulkan)
            vulkan_ok = vulkan_rc == 0 and bool(re.search(r'deviceName\s*=\s*[^\n]*T4', vulkan))
            if not vulkan_ok:
                print('AVISO: Vulkan no confirmado; se conserva OpenGL y continúa el escritorio. Revisar /tmp/pcfree-selkies/vulkan.log.', flush=True)
            session['graphics'] = {'opengl_nvidia_t4': True, 'vulkan_nvidia_t4': vulkan_ok,
                'vulkan_log': str(BASE / 'vulkan.log'),
                'gles_profile': next((line.strip() for line in renderer.splitlines()
                                      if 'OpenGL ES profile version string' in line), 'No informado por glxinfo')}
            audio_env = dict(env); audio_env.pop('PULSE_SERVER', None)
            pulse = spawn(['pulseaudio', '--daemonize=no', '--exit-idle-time=-1', '--disallow-exit',
                           '--log-target=stderr'], 'pulse', audio_env, processes, nice=-10)
            def audio_ready():
                return subprocess.run(as_user(['pactl', 'info']), env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, timeout=3).returncode == 0
            wait_for(audio_ready, 'PulseAudio', [pulse])
            sinks = capture(as_user(['pactl', 'list', 'short', 'sinks']), env=env)
            if not any(line.split()[1] == 'output' for line in sinks.splitlines() if len(line.split()) >= 2):
                try:
                    capture(as_user(['pactl', 'load-module', 'module-null-sink', *AUDIO_SINK_ARGS]), env=env)
                except Exception as exc:
                    print(f'Aviso: el sink de 48 kHz no se pudo crear ({exc}); se usa el sink simple.', flush=True)
                    capture(as_user(['pactl', 'load-module', 'module-null-sink', 'sink_name=output',
                                     'sink_properties=device.description=PC-Free']), env=env)
            capture(as_user(['pactl', 'set-default-sink', 'output']), env=env)
            capture(as_user(['pactl', 'set-default-source', 'output.monitor']), env=env)
            # flat-volumes=no keeps gains independent; 100% avoids clipping when a
            # game or the client raises its own volume at medium/high settings.
            capture(as_user(['pactl', 'set-sink-volume', 'output', '100%']), env=env)
            capture(as_user(['pactl', 'set-sink-mute', 'output', '0']), env=env)
            dbus = spawn(['dbus-daemon', '--session', '--nofork',
                          '--address=' + env['DBUS_SESSION_BUS_ADDRESS']], 'dbus', env, processes)
            def bus_ready():
                return subprocess.run(as_user(['dbus-send', '--session', '--print-reply',
                                      '--dest=org.freedesktop.DBus', '/org/freedesktop/DBus',
                                      'org.freedesktop.DBus.ListNames']), env=env,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      timeout=3).returncode == 0
            wait_for(bus_ready, 'D-Bus de escritorio', [dbus])
            desktop = spawn(['xfce4-session'], 'xfce', env, processes)
            def desktop_ready():
                result = subprocess.run(as_user(['xprop', '-root', '_NET_SUPPORTING_WM_CHECK']),
                                        env=env, capture_output=True, text=True, timeout=3)
                return result.returncode == 0 and 'window id #' in result.stdout
            wait_for(desktop_ready, 'XFCE', [desktop])
        with phase('Selkies autenticado y túnel HTTPS HTTP/2'):
            access = dict(username='pcfree', password=secrets.token_urlsafe(24), url=None)
            private_json(BASE / 'access.json', access)
            server_env = dict(env, SELKIES_BASIC_AUTH_USER=access['username'],
                              SELKIES_BASIC_AUTH_PASSWORD=access['password'],
                              SELKIES_KEYBOARD_SHORTCUTS='true',
                              SELKIES_UI_SIDEBAR_SHOW_GAMING_MODE='true',
                              SELKIES_UI_SIDEBAR_SHOW_FULLSCREEN='true',
                              SELKIES_UI_SIDEBAR_SHOW_KEYBOARD_BUTTON='true',
                              SELKIES_VIDEO_STREAMING_MODE='true|locked',
                              SELKIES_USE_CPU='false|locked', SELKIES_AUTO_GPU='nvidia',
                              SELKIES_AUDIO_ENABLED='true|locked',
                              SELKIES_AUDIO_BITRATE='96000',
                              SELKIES_AUDIO_CHANNELS='2',
                              SELKIES_AUDIO_DEVICE_NAME='output.monitor',
                              SELKIES_AUDIO_FRAME_DURATION_MS='20',
                              SELKIES_AUDIO_REDUNDANCY='true|locked',
                              SELKIES_AUDIO_REDUNDANCY_DISTANCE='2',
                              SELKIES_RATE_CONTROL_MODE='cbr')
            # NVENC FIX (Google Colab Tesla T4): SOLO afecta al proceso de Selkies.
            # Conserva LD_LIBRARY_PATH y añade las bibliotecas NVIDIA del runtime.
            # No modifica Steam, Xorg ni Cloudflare.
            server_env['LD_LIBRARY_PATH'] = ':'.join(
                p for p in (
                    server_env.get('LD_LIBRARY_PATH', ''),
                    '/usr/lib64-nvidia'
                ) if p
            )

            # PATCH 2/2: keep the stable XShm permissions shim; revert experimental system libxcb preload.
            server_env.pop('LD_PRELOAD', None)
            server_env['LD_PRELOAD'] = shm_perms
            server = spawn(['/opt/selkies/bin/selkies', '--addr=127.0.0.1', f'--port={PORT}',
                            '--web-root=' + web_root,
                            '--mode=websockets', '--enable-basic-auth=true', '--enable-https=false',
                            '--encoder=h264enc', '--use-cpu=false', '--auto-gpu=nvidia',
                            f'--framerate={framerate}', f'--video-bitrate={bitrate}',
                            '--rate-control-mode=cbr', '--keyframe-interval=0',
                            '--video-streaming-mode=true', '--video-fullcolor=false',
                            '--enable-resize=true', f'--backpressure-queue-size={backpressure_queue_size}',
                            '--congestion-control=' + ('true' if congestion_control else 'false'),
                            '--frame-ancestors=self',
                            '--use-paint-over-quality=false', '--second-screen=false',
                            '--audio-enabled=true', '--audio-bitrate=96000',
                            '--audio-channels=2', '--audio-device-name=output.monitor',
                            '--audio-frame-duration-ms=20', '--audio-redundancy=true'],
                           'selkies', server_env, processes)
            wait_for(lambda: auth_ready(access['username'], access['password']), 'Selkies + autenticación', [server], 60)
            selkies_log = (BASE / 'selkies.log').read_text(errors='replace')
            if re.search(r'X11 Access error|BadAccess|XShm.*(fail|error)', selkies_log, re.I):
                raise RuntimeError('Selkies no puede capturar la pantalla (XShm/X11); revisar selkies.log.')
            cloud = spawn([str(tunnel), 'tunnel', '--url', f'http://127.0.0.1:{PORT}',
                           '--protocol', 'http2', '--no-autoupdate'], 'cloudflared', env, processes)
            def tunnel_ready():
                log = (BASE / 'cloudflared.log').read_text()
                links = re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com', log)
                if links and 'Registered tunnel connection' in log and 'protocol=http2' in log:
                    access['url'] = links[-1]
                    return True
                return False
            # Do NOT require VM DNS/outbound reachability of the quick-tunnel URL.
            wait_for(tunnel_ready, 'Cloudflare HTTP/2', [cloud, server], 90)
            private_json(BASE / 'access.json', access)
        session['processes'] = {name: {'pid': process.pid, 'start': pid_identity(process.pid)}
                                for name, process in processes.items()}
        private_json(state, session)
        print(f'Escritorio preparado en {time.monotonic() - started:.1f} s.', flush=True)
        show_access()
        return session


if __name__ == '__main__':
    bootstrap()
