"""Optional applications. Install only; never start graphical applications."""
import hashlib
import fcntl
import json
import os
import platform
import pwd
import re
import shlex
import subprocess
import tarfile
import threading
import urllib.request
import urllib.parse
import zipfile
from pathlib import Path

BASE = Path('/tmp/pcfree-selkies')
OPTIONS = {
    'wine': ['wine64', 'wine32:i386', 'winetricks'],
    'lutris': ['lutris'],
    'java': ['openjdk-21-jre'],
    'gaming-libs': ['libsdl2-2.0-0', 'libsdl2-2.0-0:i386',
                    'libopenal1', 'libopenal1:i386', 'libvulkan1:i386',
                    'libasound2t64:i386', 'libpulse0:i386', 'libstdc++6:i386'],
    'deb-installer': ['gdebi'],
    'blender': ['blender'],
}
APPIMAGES = {
    'heroic': ('Heroic-Games-Launcher/HeroicGamesLauncher', 'Heroic'),
    'prism': ('PrismLauncher/PrismLauncher', 'Prism Launcher'),
}
EXPERIMENTAL = {'godot', 'vinegar', 'roblox'}


def command(argv, log, timeout=600):
    env = {**os.environ, 'DEBIAN_FRONTEND': 'noninteractive', 'LC_ALL': 'C'}
    for key in ('LD_PRELOAD', 'LD_LIBRARY_PATH', 'PYTHONPATH', 'PYTHONHOME'):
        env.pop(key, None)
    if argv[:2] == ['apt-get', 'install']:
        plan = subprocess.check_output(['apt-get', '-s', *argv[1:]], env=env,
                                       text=True, stderr=subprocess.STDOUT, timeout=120)
        for line in plan.splitlines():
            if line.startswith('Remv '):
                raise RuntimeError('APT propone eliminar paquetes; se canceló la instalación.')
            if line.startswith('Inst '):
                package = line.split()[1].split(':')[0]
                if 'nvidia' in package or package.startswith(('linux-image', 'linux-modules', 'linux-headers')):
                    raise RuntimeError('APT propone modificar GPU/kernel; se canceló la instalación.')
        origins = subprocess.check_output(['apt-get', '--print-uris', '--download-only', *argv[1:]],
                                          env=env, text=True, stderr=subprocess.STDOUT, timeout=120)
        for uri in re.findall(r"^'([^']+)'", origins, re.MULTILINE):
            parsed = urllib.parse.urlparse(uri)
            host = parsed.hostname or ''
            ubuntu = host in {'archive.ubuntu.com', 'security.ubuntu.com', 'ports.ubuntu.com'} or host.endswith('.archive.ubuntu.com')
            nvidia = host == 'developer.download.nvidia.com' and parsed.scheme == 'https' and parsed.path.startswith('/compute/cuda/repos/ubuntu2404/x86_64/')
            if parsed.scheme not in {'http', 'https'} or not (ubuntu or nvidia) or parsed.username or parsed.password:
                raise RuntimeError('La instalación requiere paquetes de repositorios oficiales Ubuntu/NVIDIA.')
    with log.open('a') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT,
                                env=env,
                                timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'Falló {shlex.join(argv)}; revisar {log}\n'
                           + log.read_text(errors='replace')[-3000:])


def shortcut(session, name, executable, category='Game', icon='applications-games'):
    home = Path(session['home'])
    desktop = home / 'Desktop'
    desktop.mkdir(parents=True, exist_ok=True)
    path = desktop / (name.replace(' ', '-') + '.desktop')
    # Quote Desktop Entry arguments, independently of shell quoting.
    def quote(arg):
        return '"' + str(arg).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'
    launcher = session.get('run_launcher', '/usr/local/bin/pcfree-run')
    path.write_text('[Desktop Entry]\nType=Application\nVersion=1.0\n'
                    f'Name={name}\nExec={quote(launcher)} {quote(executable)}\n'
                    f'Icon={icon}\nTerminal=false\nCategories={category};\n')
    path.chmod(0o755)
    account = pwd.getpwnam(session['user'])
    os.chown(path, account.pw_uid, account.pw_gid)
    env = session['env']
    subprocess.run(['runuser', '-u', session['user'], '--', 'env',
                    *[f'{k}={v}' for k, v in env.items()],
                    'gio', 'set', str(path), 'metadata::trusted', 'true'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def official_appimage(option, session):
    repository, label = APPIMAGES[option]
    directory = BASE / 'apps' / option
    directory.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repository}/releases/latest',
        headers={'User-Agent': 'PC-Free-T4'})
    with urllib.request.urlopen(request, timeout=45) as response:
        release = json.load(response)
    matches = [a for a in release.get('assets', [])
               if a['name'].lower().endswith('.appimage')
               and ('x86_64' in a['name'].lower() or 'amd64' in a['name'].lower())
               and 'portable' not in a['name'].lower()]
    if len(matches) != 1:
        raise RuntimeError(f'No se pudo elegir el AppImage oficial de {repository}: '
                           + ', '.join(a['name'] for a in matches))
    asset = matches[0]
    url = asset['browser_download_url']
    if not url.startswith(f'https://github.com/{repository}/releases/download/'):
        raise RuntimeError('El enlace del paquete no pertenece al repositorio oficial.')
    image = directory / Path(asset['name']).name
    if not image.exists():
        temporary = image.with_suffix(image.suffix + '.part')
        urllib.request.urlretrieve(url, temporary)
        digest = asset.get('digest') or ''
        if digest.startswith('sha256:'):
            sha = hashlib.sha256()
            with temporary.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    sha.update(block)
            if sha.hexdigest() != digest.partition(':')[2]:
                temporary.unlink()
                raise RuntimeError('La descarga no coincide con el SHA-256 oficial.')
        temporary.replace(image)
    image.chmod(0o755)
    extracted = directory / 'squashfs-root'
    log = directory / 'install.log'
    if not (extracted / 'AppRun').exists():
        # Native extraction avoids FUSE. Runs only the official installer runtime.
        with log.open('w') as stream:
            result = subprocess.run([str(image), '--appimage-extract'], cwd=directory,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        if result.returncode or not (extracted / 'AppRun').exists():
            raise RuntimeError(f'No se pudo extraer el AppImage; revisar {log}.')
    shortcut(session, label, str(extracted / 'AppRun'))
    print(f'{label} {release["tag_name"]}: instalado, sin abrir. '
          'Su sandbox y los juegos requieren pruebas en este entorno.')


def install_godot(session):
    directory = BASE / 'apps/godot'
    directory.mkdir(parents=True, exist_ok=True)
    repository = 'godotengine/godot'
    request = urllib.request.Request(f'https://api.github.com/repos/{repository}/releases/latest',
                                     headers={'User-Agent': 'PC-Free-T4'})
    with urllib.request.urlopen(request, timeout=45) as response:
        release = json.load(response)
    candidates = [a for a in release['assets']
                  if a['name'].endswith('_linux.x86_64.zip') and 'mono' not in a['name'].lower()]
    if len(candidates) != 1:
        raise RuntimeError('No se encontró un binario Linux x86_64 de Godot en su publicación oficial.')
    asset = candidates[0]
    if not asset['browser_download_url'].startswith(f'https://github.com/{repository}/releases/download/'):
        raise RuntimeError('Origen de Godot inesperado.')
    archive = directory / Path(asset['name']).name
    if not archive.exists():
        urllib.request.urlretrieve(asset['browser_download_url'], archive)
    with zipfile.ZipFile(archive) as bundle:
        entries = [item for item in bundle.infolist() if not item.is_dir()]
        if len(entries) != 1 or '/' in entries[0].filename or '\\' in entries[0].filename:
            raise RuntimeError('Estructura del paquete Godot inesperada.')
        executable = directory / entries[0].filename
        with bundle.open(entries[0]) as source, executable.open('wb') as destination:
            import shutil
            shutil.copyfileobj(source, destination)
    executable.chmod(0o755)
    shortcut(session, 'Godot', str(executable), 'Development', 'applications-development')
    print(f'Godot {release["tag_name"]}: instalado, sin abrir. '
          'Vulkan NVIDIA se prepara en el arranque; Compatibility usa OpenGL si el proyecto lo requiere.')


def install_vinegar(session):
    """Official native source build; Studio/Wine downloads start only when opened."""
    directory = BASE / 'apps/vinegar'
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / 'install.log'
    packages = ['build-essential', 'git', 'make', 'pkg-config', 'gettext',
                'libgtk-4-dev', 'libadwaita-1-dev', 'libvulkan-dev', 'libglib2.0-dev-bin']
    command(['apt-get', 'update', '-qq'], log)
    command(['apt-get', 'install', '-y', '--no-install-recommends', *packages], log)
    request = urllib.request.Request('https://go.dev/dl/?mode=json', headers={'User-Agent': 'PC-Free-T4'})
    with urllib.request.urlopen(request, timeout=45) as response:
        releases = json.load(response)
    choices = [release for release in releases if release.get('stable')
               and tuple(int(n) for n in release['version'][2:].split('.')[:2]) >= (1, 26)]
    if not choices:
        raise RuntimeError('Vinegar 1.9.4 requiere Go >=1.26; no se encontró un compilador estable oficial.')
    toolchain = next(f for f in choices[0]['files'] if f['os'] == 'linux'
                     and f['arch'] == 'amd64' and f['kind'] == 'archive')
    tools = directory / 'toolchain'
    tools.mkdir(exist_ok=True)
    archive = tools / toolchain['filename']
    if not (tools / 'go/bin/go').exists():
        urllib.request.urlretrieve('https://go.dev/dl/' + toolchain['filename'], archive)
        sha = hashlib.sha256()
        with archive.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                sha.update(block)
        if sha.hexdigest() != toolchain['sha256']:
            archive.unlink()
            raise RuntimeError('SHA-256 del compilador Go no válido.')
        with tarfile.open(archive) as bundle:
            bundle.extractall(tools, filter='data')
        archive.unlink()
    source = directory / 'source'
    if not source.exists():
        command(['git', 'clone', '--branch', 'v1.9.4', '--depth', '1',
                 'https://github.com/vinegarhq/vinegar.git', str(source)], log)
    prefix = directory / 'installed'
    env = {**os.environ, 'PATH': str(tools / 'go/bin') + ':' + os.environ.get('PATH', '')}
    env.pop('LD_PRELOAD', None)
    for argv in [['make', '-j2', 'PREFIX=' + str(prefix)],
                 ['make', 'install', 'PREFIX=' + str(prefix)]]:
        with log.open('a') as stream:
            result = subprocess.run(argv, cwd=source, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=1200)
        if result.returncode:
            raise RuntimeError(f'Falló la compilación de Vinegar; revisar {log}.')
    shortcut(session, 'Roblox Studio - Vinegar', str(prefix / 'bin/vinegar'),
             'Development', str(prefix / 'share/icons/hicolor/scalable/apps/org.vinegarhq.Vinegar.svg'))
    print('Vinegar 1.9.4: instalado desde el código oficial, sin abrir. '
          'Wine y Roblox Studio se descargan al abrirlo. Experimental: Studio no validado en Colab; '
          'Vinegar no ejecuta Roblox Player.')


def sober_requirements(cpuinfo=None, machine=None, kernel=None):
    """Validate hardware, not emulate CPU features or bypass kernel restrictions."""
    machine = machine or platform.machine()
    kernel = kernel or platform.release()
    if machine not in {'x86_64', 'amd64'}:
        raise RuntimeError('Sober requiere CPU x86-64; ARM no está soportado.')
    match = re.match(r'(\d+)\.(\d+)', kernel)
    if not match or tuple(map(int, match.groups())) < (5, 11):
        raise RuntimeError('Sober requiere kernel Linux >=5.11.')
    cpuinfo = Path('/proc/cpuinfo').read_text() if cpuinfo is None else cpuinfo
    flags = [set(line.partition(':')[2].split()) for line in cpuinfo.splitlines()
             if line.partition(':')[0].strip() == 'flags']
    if not flags or not all('sse4_1' in item for item in flags):
        raise RuntimeError('La CPU asignada no ofrece SSE4.1. No se puede añadir con un paquete; usar otra VM.')
    return {'sse4_1': True, 'sse4_2': all('sse4_2' in item for item in flags), 'kernel': kernel}


def ensure_flatpak_system_bus(log):
    """Flatpak consults parental-control policy even for --user installs."""
    def ready():
        result = subprocess.run(['dbus-send', '--system', '--print-reply',
                                 '--dest=org.freedesktop.DBus', '/org/freedesktop/DBus',
                                 'org.freedesktop.DBus.ListNames'], capture_output=True,
                                text=True, timeout=5)
        return result.returncode == 0
    with (BASE / 'flatpak-system-bus.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if ready():
            return
        if Path('/run/dbus/system_bus_socket').exists():
            raise RuntimeError('El bus de sistema existente no responde; no se reemplaza automáticamente.')
        Path('/run/dbus').mkdir(mode=0o755, parents=True, exist_ok=True)
        command(['dbus-daemon', '--system', '--fork', '--nopidfile'], log, timeout=15)
        if not ready():
            raise RuntimeError('D-Bus de sistema no disponible para Flatpak; revisar install-roblox.log.')


def install_roblox(session):
    """Sober's official Flatpak only where the required kernel sandbox is available."""
    requirements = sober_requirements()
    result = subprocess.run(['runuser', '-u', session['user'], '--', 'unshare',
                             '--user', '--map-root-user', '--mount', '--pid', '--fork', 'true'],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise RuntimeError('Roblox Player necesita Sober/Flatpak, pero esta VM no permite '
                           'el sandbox de namespaces. No se instala un cliente inoperante ni se '
                           'desactiva el sandbox. Fuente: https://sober.vinegarhq.org/')
    log = BASE / 'install-roblox.log'
    command(['apt-get', 'update', '-qq'], log)
    command(['apt-get', 'install', '-y', '--no-install-recommends', 'flatpak'], log)
    try:
        # unshare alone can succeed while this required proc mount is denied.
        # Probe a real Bubblewrap sandbox before downloading large runtimes.
        command(['runuser', '-u', session['user'], '--', 'bwrap',
                 '--unshare-user', '--unshare-pid', '--ro-bind', '/', '/',
                 '--proc', '/proc', '--dev', '/dev', '--', '/usr/bin/true'], log, timeout=15)
    except RuntimeError as error:
        raise RuntimeError('Flatpak está instalado, pero esta VM no permite el sandbox '
                           'Bubblewrap con /proc. No se descargan los runtimes ni se fuerza '
                           'Roblox sin sandbox. Revisar install-roblox.log; usar un entorno '
                           'Linux que permita Flatpak.') from error
    ensure_flatpak_system_bus(log)
    version = session.get('driver_version', '')
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
        raise RuntimeError('No se conoce la versión NVIDIA exacta para Flatpak; no usar renderizado por software.')
    driver = 'nvidia-' + version.replace('.', '-')
    # Flatpak cannot use the host's isolated LD_LIBRARY_PATH/ICD. It needs its
    # own GL extension matching the loaded NVIDIA kernel driver exactly.
    env = {k: v for k, v in session['env'].items()
           if k not in {'LD_PRELOAD', 'LD_LIBRARY_PATH', 'VK_DRIVER_FILES', 'VK_ICD_FILENAMES', '__EGL_VENDOR_LIBRARY_FILENAMES', 'SELKIES_INTERPOSER'}}
    env['FLATPAK_GL_DRIVERS'] = driver + ':default'
    prefix = ['runuser', '-u', session['user'], '--', 'env',
              '-u', 'LD_PRELOAD', '-u', 'LD_LIBRARY_PATH', '-u', 'VK_DRIVER_FILES', '-u', 'VK_ICD_FILENAMES',
              '-u', '__EGL_VENDOR_LIBRARY_FILENAMES',
              *[f'{k}={v}' for k, v in env.items()], 'flatpak', '--user']
    command([*prefix, 'remote-add', '--if-not-exists', 'flathub',
             'https://flathub.org/repo/flathub.flatpakrepo'], log)
    command([*prefix, 'install', '-y', '--noninteractive', 'flathub',
             f'org.freedesktop.Platform.GL.{driver}//1.4'], log, timeout=1200)
    command([*prefix, 'install', '-y', '--noninteractive', 'flathub',
             'org.vinegarhq.Sober'], log, timeout=1200)
    # Runs only /usr/bin/true inside the real app sandbox, never opens Roblox.
    command([*prefix, 'run', '--command=true', 'org.vinegarhq.Sober'], log, timeout=30)
    wrapper = BASE / 'apps/sober-launch'
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text('#!/bin/sh\nexec env -u LD_PRELOAD -u LD_LIBRARY_PATH '
                       '-u VK_DRIVER_FILES -u VK_ICD_FILENAMES -u __EGL_VENDOR_LIBRARY_FILENAMES '
                       f'FLATPAK_GL_DRIVERS={shlex.quote(driver + ":default")} '
                       'flatpak run org.vinegarhq.Sober "$@"\n')
    wrapper.chmod(0o755)
    shortcut(session, 'Roblox - Sober', str(wrapper))
    (BASE / 'sober-requirements.json').write_text(json.dumps({**requirements, 'flatpak_gl_driver': driver,
        'sandbox_smoke_test': True, 'game_validated': False}, indent=2))
    print('Sober instalado, sin abrir. Proyecto comunitario no respaldado por Roblox; '
          'inicio de sesión, juego y controladores todavía requieren pruebas.')


_roblox_thread = None


def roblox_background(session):
    """Keep desktop access available while downloading the Flatpak runtimes."""
    global _roblox_thread
    if _roblox_thread is not None and _roblox_thread.is_alive():
        print('Sober: instalación ya en curso.')
        return _roblox_thread
    def worker():
        status = BASE / 'sober-status.txt'
        try:
            with (BASE / 'sober-install.lock').open('w') as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    print('Sober: otra instalación está en curso.', flush=True)
                    return
                install_roblox(session)
                status.write_text('Instalado; abrir Roblox - Sober. Roblox se instala en el primer inicio.\n')
        except Exception as error:
            status.write_text('Instalación incompleta: ' + str(error) + '\n')
            print('Sober: ' + str(error), flush=True)
    BASE.mkdir(exist_ok=True)
    (BASE / 'sober-status.txt').write_text('Instalando Flatpak, runtime NVIDIA y Sober en segundo plano.\n')
    _roblox_thread = threading.Thread(target=worker, name='pcfree-sober', daemon=True)
    _roblox_thread.start()
    print('Sober/Flatpak: descarga en segundo plano; el escritorio ya está disponible.', flush=True)
    return _roblox_thread


def install_app(option, session):
    if os.geteuid() != 0:
        raise RuntimeError('Ejecuta esta celda de instalación desde Colab.')
    if option not in OPTIONS and option not in APPIMAGES and option not in EXPERIMENTAL:
        raise ValueError('Opción desconocida: ' + option)
    BASE.mkdir(exist_ok=True)
    log = BASE / f'install-{option}.log'
    if option in EXPERIMENTAL:
        {'godot': install_godot, 'vinegar': install_vinegar, 'roblox': install_roblox}[option](session)
        return
    if option in APPIMAGES:
        if option == 'prism':
            install_app('java', session)
        official_appimage(option, session)
        return
    packages = OPTIONS[option]
    if any(name.endswith(':i386') for name in packages):
        command(['dpkg', '--add-architecture', 'i386'], log)
    command(['apt-get', 'update', '-qq'], log)
    command(['apt-get', 'install', '-y', '--no-install-recommends', *packages], log)
    if option == 'wine':
        shortcut(session, 'Wine Configuration', '/usr/bin/winecfg', 'Settings', 'wine')
        shortcut(session, 'Winetricks', '/usr/bin/winetricks', 'Settings', 'wine')
    elif option == 'lutris':
        shortcut(session, 'Lutris', '/usr/bin/lutris', icon='lutris')
    elif option == 'deb-installer':
        shortcut(session, 'Instalador DEB', '/usr/bin/gdebi-gtk', 'System', 'package-x-generic')
    elif option == 'blender':
        shortcut(session, 'Blender', '/usr/bin/blender', 'Graphics', 'blender')
    print(f'{option}: instalado, sin abrir aplicaciones. Registro: {log}')
    if option == 'wine':
        print('Wine no equivale a Windows. DXVK/VKD3D requieren Vulkan NVIDIA '
              'verificado y bibliotecas NVIDIA de 32/64 bits; usa la celda de Steam '
              'para preparar el soporte multiarch. No se instalan runners sin verificar.')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('option', choices=sorted([*OPTIONS, *APPIMAGES, *EXPERIMENTAL]))
    parser.add_argument('--session', default=str(BASE / 'session.json'))
    args = parser.parse_args()
    install_app(args.option, json.loads(Path(args.session).read_text()))
