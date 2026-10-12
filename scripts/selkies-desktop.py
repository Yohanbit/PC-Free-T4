"""Standalone Ubuntu 24.04/T4 desktop. Importing this module performs no setup.

Only bootstrap() installs/starts services. No notebook globals, Drive, keepalive,
driver installation, or automatic app windows. Logs stay on the ephemeral VM.
"""
import base64
import contextlib
import fcntl
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
SELKIES_VERSION = '2.0.0'
SELKIES_DEB_VERSION = '2.0.0-1~ubuntu24.04'
SELKIES_URL = ('https://github.com/selkies-project/selkies/releases/download/'
               f'{SELKIES_VERSION}/selkies-{SELKIES_VERSION}-ubuntu24.04-amd64.deb')
CLOUDFLARED_URL = 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64'
FIREFOX_URL = 'https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=es-ES'
PACKAGES = ['xserver-xorg-core', 'xfce4-session', 'xfwm4', 'xfce4-panel',
            'xfdesktop4', 'xfce4-settings', 'thunar', 'xfce4-terminal',
            'dbus-x11', 'mesa-utils', 'vulkan-tools', 'x11-utils', 'x11-xserver-utils', 'xauth',
            'pulseaudio', 'pulseaudio-utils', 'ca-certificates', 'python3.12',
            'libgtk-3-0t64', 'libdbus-glib-1-2', 'libasound2t64', 'zenity', 'sudo']


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
    gpu = capture(['nvidia-smi', '--query-gpu=name,driver_version,pci.bus_id', '--format=csv,noheader']).strip().splitlines()
    if len(gpu) != 1:
        raise RuntimeError('Esta receta requiere una sola GPU Tesla T4.')
    name, driver, bus = (value.strip() for value in gpu[0].split(','))
    if 'T4' not in name or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', driver):
        raise RuntimeError('GPU/versión NVIDIA no compatible.')
    if Path('/tmp/.X11-unix/X98').exists() or Path('/tmp/.X98-lock').exists():
        raise RuntimeError('Ya existe Xorg :98. No se reinicia ni se reinstala la sesión activa.')
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
            raise RuntimeError('APT propone eliminar paquetes; operación cancelada.')
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
    actual = capture(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader']).strip()
    if actual != driver:
        raise RuntimeError('El controlador del kernel cambió durante la preparación.')
    return root, ':'.join(libraries)


def prepare_user(root, libraries):
    try:
        account = pwd.getpwnam(USER)
    except KeyError:
        logged(['useradd', '--create-home', '--home-dir', str(BASE / 'home'), '--shell', '/bin/bash', USER])
        account = pwd.getpwnam(USER)
    if account.pw_uid == 0:
        raise RuntimeError('El usuario de escritorio no puede ser root.')
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
    for item in (home / '.config', pulse_config, cookie):
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
    """Rewrite the official isolated NVIDIA ICD to its absolute extracted library.

    Do not register it in /usr/share, where it could affect the managed host.
    Keep the official API version and other fields; no guessed Vulkan version.
    """
    candidates = list(root.rglob('nvidia_icd.json'))
    if len(candidates) != 1:
        raise RuntimeError('ICD Vulkan NVIDIA oficial no encontrado o ambiguo.')
    document = json.loads(candidates[0].read_text())
    library = root / 'usr/lib/x86_64-linux-gnu/libGLX_nvidia.so.0'
    if not library.is_file() or not document.get('ICD', {}).get('api_version'):
        raise RuntimeError('ICD/biblioteca Vulkan NVIDIA incompletos.')
    document['ICD']['library_path'] = str(library)
    destination = BASE / 'nvidia-vulkan64.json'
    destination.write_text(json.dumps(document, indent=2) + '\n')
    destination.chmod(0o644)  # Not secret; the unprivileged Vulkan loader reads it.
    return str(destination)


def as_user(argv):
    return ['runuser', '-u', USER, '--', *argv]


def spawn(argv, name, env, processes, user=True):
    with (BASE / (name + '.log')).open('a') as log:
        process = subprocess.Popen(as_user(argv) if user else argv, env=env,
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
    raise SystemExit('Usuario de escritorio requerido.')
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


def firefox_background(session):
    def worker():
        try:
            destination = BASE / 'firefox'; destination.mkdir(exist_ok=True)
            archive = destination / 'firefox.tar'
            if not (destination / 'firefox/firefox').exists():
                download(FIREFOX_URL, archive)
                with tarfile.open(archive) as bundle:
                    bundle.extractall(destination, filter='data')
                archive.unlink()
            command = '/usr/local/bin/pcfree-firefox'
            Path(command).write_text('#!/bin/sh\nexec /usr/local/bin/pcfree-run '
                                     + shlex.quote(str(destination / 'firefox/firefox')) + ' "$@"\n')
            Path(command).chmod(0o755)
            shortcut(session, 'Firefox', 'Firefox', command + ' %u',
                     str(destination / 'firefox/browser/chrome/icons/default/default128.png'))
            (BASE / 'firefox-status.txt').write_text('listo\n')
            print('Firefox listo: icono instalado; no se abrió ninguna ventana.', flush=True)
        except Exception as error:
            (BASE / 'firefox-status.txt').write_text('error: ' + str(error) + '\n')
            print(f'Firefox: descarga/instalación fallida: {error}. Reintentar con firefox_background(SESSION).', flush=True)
    thread = threading.Thread(target=worker, name='pcfree-firefox', daemon=True)
    thread.start()
    return thread


def show_access():
    access = json.loads((BASE / 'access.json').read_text())
    print('\nAcceso privado — no guardar estas salidas en GitHub:', flush=True)
    print('URL:', access['url'], '\nUsuario:', access['username'], '\nContraseña:', access['password'], flush=True)
    state = BASE / 'session.json'
    settings = json.loads(state.read_text()).get('settings', {}) if state.exists() else {}
    fps, kbps = settings.get('framerate', 30), settings.get('bitrate', 2000)
    print(f'720p · H.264 · {fps} fps · {kbps} kbps iniciales. Ajustar según red; latencia no garantizada.')
    firefox = 'descarga en segundo plano' if settings.get('firefox', True) else 'desactivado'
    print(f'Registros: {BASE} | Firefox: {firefox}, sin abrir ventanas.')


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


def bootstrap(firefox=True, framerate=30, bitrate=2000):
    if not isinstance(framerate, int) or not 1 <= framerate <= 60 or not isinstance(bitrate, int) or not 500 <= bitrate <= 20000:
        raise ValueError('FPS: 1–60; bitrate: 500–20000 kbps.')
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
            deb = BASE / 'selkies.deb'; download(SELKIES_URL, deb)
            safe_apt_install([str(deb)], validated_local_deb=deb)
            # Only fix the private package venv, NEVER /usr/bin/python3.
            python = Path('/opt/selkies/bin/python3')
            if not python.is_symlink():
                raise RuntimeError('Python privado Selkies inesperado; no modificar Python del sistema.')
            python.unlink(); python.symlink_to('/usr/bin/python3.12')
            capture(['/opt/selkies/bin/selkies', '--help'])
            tunnel = BASE / 'cloudflared'; download(CLOUDFLARED_URL, tunnel); tunnel.chmod(0o755)
        with phase('Bibliotecas 3D exactas, aisladas del kernel'):
            root, libraries = graphics(driver)
            session, env = prepare_user(root, libraries)
            icd = vulkan_icd(root)
            for key in ('VK_DRIVER_FILES', 'VK_ICD_FILENAMES'):
                env[key] = icd
                session['env'][key] = icd
            session['driver_version'] = driver
            session['settings'] = {'framerate': framerate, 'bitrate': bitrate, 'firefox': firefox}
            desktop_files(session)
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
  Virtual 1280 720
 EndSubSection
EndSection
'''.replace('BUSID', busid))
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
            if 'NVIDIA' not in renderer or 'T4' not in renderer:
                raise RuntimeError('OpenGL T4 no confirmado; revisar Xorg.log.')
            vulkan = capture(as_user(['vulkaninfo', '--summary']), env=env, timeout=30)
            (BASE / 'vulkan.log').write_text(vulkan)
            if not re.search(r'deviceName\s*=\s*[^\n]*T4', vulkan):
                raise RuntimeError('Vulkan64 T4 no confirmado; revisar vulkan.log e ICD aislado.')
            audio_env = dict(env); audio_env.pop('PULSE_SERVER', None)
            pulse = spawn(['pulseaudio', '--daemonize=no', '--exit-idle-time=-1', '--disallow-exit',
                           '--log-target=stderr'], 'pulse', audio_env, processes)
            def audio_ready():
                return subprocess.run(as_user(['pactl', 'info']), env=env, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, timeout=3).returncode == 0
            wait_for(audio_ready, 'PulseAudio', [pulse])
            sinks = capture(as_user(['pactl', 'list', 'short', 'sinks']), env=env)
            if not any(line.split()[1] == 'output' for line in sinks.splitlines() if len(line.split()) >= 2):
                capture(as_user(['pactl', 'load-module', 'module-null-sink', 'sink_name=output',
                                 'sink_properties=device.description=PC-Free']), env=env)
            capture(as_user(['pactl', 'set-default-sink', 'output']), env=env)
            capture(as_user(['pactl', 'set-default-source', 'output.monitor']), env=env)
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
                              SELKIES_BASIC_AUTH_PASSWORD=access['password'])
            server_env.pop('LD_PRELOAD', None)
            server = spawn(['/opt/selkies/bin/selkies', '--addr=127.0.0.1', f'--port={PORT}',
                            '--mode=websockets', '--enable-basic-auth=true', '--enable-https=false',
                            '--encoder=h264enc', f'--framerate={framerate}', f'--video-bitrate={bitrate}',
                            '--enable-resize=false', '--backpressure-queue-size=2'], 'selkies', server_env, processes)
            wait_for(lambda: auth_ready(access['username'], access['password']), 'Selkies + autenticación', [server], 60)
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
        if firefox:
            firefox_background(session)
        return session


if __name__ == '__main__':
    bootstrap()
