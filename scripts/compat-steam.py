#!/usr/bin/env python3
"""Steam oficial opcional; instala, pero no abre ventanas.

API: install_steam(session), install_gamepads(session) (sin Steam).
Estado: /tmp/pcfree-selkies/session.json.
Opciones en session['steam']: gamepads=False, repair_client=False,
    bwrap=None (ruta a un proot-bwrap ya instalado y revisado).
No cambia el controlador del kernel, libudev del sistema ni el Python global.

Fuentes: repo.steampowered.com/steam/archive/stable/steam_latest.deb;
github.com/selkies-project/selkies/tree/2.1.0/addons/fake-udev;
github.com/selkies-project/proot-bwrap (alternativa, no frontera de seguridad).
fake-udev sirve para mandos; no es una reparación demostrada del login.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import posixpath
import pwd
import re
import shlex
import shutil
import struct
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request


STEAM_DEB = 'https://repo.steampowered.com/steam/archive/stable/steam_latest.deb'
SELKIES_TAG = '2.1.0'
GE_PROTON_VERSION = 'GE-Proton11-11'
GE_PROTON_URL = ('https://github.com/GloriousEggroll/proton-ge-custom/releases/download/'
                 f'{GE_PROTON_VERSION}/{GE_PROTON_VERSION}-x86_64.tar.gz')
GE_PROTON_SHA512 = ('45721a7b625b2404d8896bb5e2a8b87fc9623a394873a6dd6b900c839681d5c0'
                    '1ec694ca00d003fc9c733c5f6c5648af8171985656f9fa47e20999fbebdbe235')
TRIPLETS = {'amd64': 'x86_64-linux-gnu', 'i386': 'i386-linux-gnu'}


def _run(argv, *, cwd=None, log=None, timeout=600, env=None, host_gpu=False):
    """APT/build sin heredar preloads del escritorio ni imprimir credenciales."""
    child_env = dict(os.environ)
    child_env.update(env or {})
    child_env.update(DEBIAN_FRONTEND='noninteractive', LC_ALL='C')
    for key in ('LD_PRELOAD', 'PYTHONHOME', 'PYTHONPATH'):
        child_env.pop(key, None)
    if host_gpu:
        # Sólo nvidia-smi necesita NVML del host Colab; APT/build quedan limpios.
        if Path(argv[0]).name != 'nvidia-smi':
            raise ValueError('host_gpu sólo está permitido para nvidia-smi.')
        paths = [part for part in child_env.get('LD_LIBRARY_PATH', '').split(':') if part]
        paths += [part for part in os.environ.get('LD_LIBRARY_PATH', '').split(':') if part]
        child_env['LD_LIBRARY_PATH'] = ':'.join(dict.fromkeys(paths + ['/usr/lib64-nvidia']))
    else:
        child_env.pop('LD_LIBRARY_PATH', None)
    if argv[0] == 'apt-get':
        argv = [argv[0], '-o', 'APT::Get::AllowUnauthenticated=false',
                '-o', 'Acquire::AllowInsecureRepositories=false',
                '-o', 'Acquire::AllowDowngradeToInsecureRepositories=false', *argv[1:]]
    result = subprocess.run(argv, cwd=cwd, env=child_env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=timeout)
    if log:
        with Path(log).open('a') as stream:
            stream.write('$ ' + shlex.join(map(str, argv)) + '\n' + result.stdout + '\n')
    if result.returncode:
        raise RuntimeError(f"Falló {argv[0]} ({result.returncode}). "
                           f"Revisar {log or 'la salida'}: {result.stdout[-1800:]}")
    return result.stdout.strip()


def _official_apt_uri(uri):
    """Mismos orígenes que el núcleo; /./ de APT es válido, /../ no."""
    parsed = urllib.parse.urlparse(uri)
    if (parsed.username or parsed.password or parsed.port not in (None, 80, 443)
            or parsed.query or parsed.fragment):
        return False
    path = urllib.parse.unquote(parsed.path)
    if '..' in path.split('/'):
        return False
    ubuntu = (parsed.scheme in ('http', 'https') and
              (parsed.hostname in ('archive.ubuntu.com', 'security.ubuntu.com', 'ports.ubuntu.com')
               or (parsed.hostname or '').endswith('.archive.ubuntu.com')))
    nvidia = (parsed.scheme == 'https' and parsed.port in (None, 443) and
              parsed.hostname == 'developer.download.nvidia.com' and
              path.startswith('/compute/cuda/repos/ubuntu2404/x86_64/'))
    return ubuntu or nvidia


def _safe_install(packages, log):
    plan = _run(['apt-get', '-s', 'install', '-y', '--no-install-recommends', *packages], log=log)
    for line in plan.splitlines():
        if line.startswith('Remv '):
            raise RuntimeError('APT propone eliminar paquetes; operación cancelada.')
        if line.startswith('Inst '):
            name = line.split()[1].split(':')[0]
            if ('nvidia' in name or name.startswith(('linux-image', 'linux-modules',
                                                   'linux-headers', 'linux-generic', 'linux-virtual'))):
                raise RuntimeError(f'APT propone cambiar {name}; no se modifica el kernel/GPU del host.')
    origins = _run(['apt-get', '--print-uris', '--download-only', 'install', '-y',
                    '--no-install-recommends', *packages], log=log)
    for uri in re.findall(r"^'([^']*)'", origins, re.MULTILINE):
        if not _official_apt_uri(uri):
            raise RuntimeError('APT propone un origen no oficial; operación cancelada.')
    _run(['apt-get', 'install', '-y', '--no-install-recommends', *packages], log=log)


def _download(url, target):
    # HTTPS, hosts oficiales; nunca ejecutar un instalador remoto mediante pipe.
    with urllib.request.urlopen(url, timeout=90) as response:
        if urllib.parse.urlparse(response.url).hostname not in {
                'repo.steampowered.com', 'github.com', 'codeload.github.com',
                'objects.githubusercontent.com', 'release-assets.githubusercontent.com'}:
            raise RuntimeError('Redirección de descarga fuera de los hosts oficiales.')
        with Path(target).open('wb') as stream:
            shutil.copyfileobj(response, stream)


def _elf(path, arch):
    with Path(path).open('rb') as stream:
        head = stream.read(20)
    expected = (2, 62) if arch == 'amd64' else (1, 3)
    if (len(head) != 20 or head[:4] != b'\x7fELF' or head[5] != 1 or
            (head[4], struct.unpack('<H', head[18:20])[0]) != expected):
        raise RuntimeError(f'Biblioteca ELF incompatible ({arch}): {path}')


def _owned_write(path, text, account, executable=False):
    path = Path(path)
    _user_directory(path.parent, account)
    path.write_text(text)
    path.chmod(0o755 if executable else 0o644)
    os.chown(path, account.pw_uid, account.pw_gid)


def _user_directory(path, account):
    missing = []
    cursor = Path(path)
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o755)
        os.chown(directory, account.pw_uid, account.pw_gid)


def _exact_package(package, arch, driver, log):
    lines = _run(['apt-cache', 'madison', f'{package}:{arch}'], log=log)
    versions = [line.split('|')[1].strip() for line in lines.splitlines()
                if len(line.split('|')) >= 3]
    candidates = [v for v in versions if v.split(':')[-1].split('-')[0] == driver]
    if not candidates:
        raise RuntimeError(f'Falta {package}:{arch} para NVIDIA {driver} en APT. '
                           'Habilitar un repositorio oficial Ubuntu/NVIDIA con esa versión; '
                           'no instalar otro controlador ni sustituir por una versión distinta.')
    # APT ordena sus resultados; no asumir que la revisión Ubuntu es la de otra arquitectura.
    return candidates[0]


def _graphics(base, driver, log):
    """Extrae sólo GL/gpucomp; no instala metapaquetes NVIDIA, DKMS o módulos."""
    branch = driver.split('.')[0]
    root = base / 'nvidia' / driver
    root.mkdir(parents=True, exist_ok=True)
    specs = []
    for arch in TRIPLETS:
        package = f'libnvidia-gl-{branch}'
        version = _exact_package(package, arch, driver, log)
        specs.append((package, arch, version))
        # Algunas ramas separan gpucomp; leer la dependencia de la versión exacta.
        metadata = _run(['apt-cache', 'show', f'{package}:{arch}={version}'], log=log)
        dependencies = re.findall(r'libnvidia-gpucomp-[0-9]+', metadata)
        for dependency in sorted(set(dependencies)):
            specs.append((dependency, arch,
                          _exact_package(dependency, arch, driver, log)))
    # Resolver todos los orígenes ANTES de descargar; APT verifica hashes contra
    # metadatos autenticados. No añadir claves, trusted=yes ni PPAs.
    for package, arch, version in specs:
        origins = _run(['apt-get', '--print-uris', 'download', f'{package}:{arch}={version}'], log=log)
        uris = re.findall(r"^'([^']+)'", origins, re.MULTILINE)
        if not uris or not all(_official_apt_uri(uri) for uri in uris):
            raise RuntimeError(f'{package}:{arch}: origen NVIDIA/Ubuntu no permitido.')
    with tempfile.TemporaryDirectory(prefix='download-', dir=base) as temporary:
        for package, arch, version in specs:
            _run(['apt-get', 'download', f'{package}:{arch}={version}'],
                 cwd=temporary, log=log)
        for deb in sorted(Path(temporary).glob('*.deb')):
            _run(['dpkg-deb', '-x', str(deb), str(root)], log=log)
    directories = []
    for arch, triplet in TRIPLETS.items():
        directory = root / 'usr/lib' / triplet
        for library in ('libGLX_nvidia.so.0', 'libEGL_nvidia.so.0'):
            _elf(directory / library, arch)
        directories.append(str(directory))
    # El mismo nombre se resuelve con el ELF correcto en cada proceso. No fijar
    # una ruta absoluta amd64 en el ICD que también utilizará Steam de 32 bits.
    icd = root / 'share/vulkan/icd.d/nvidia.json'
    icd.parent.mkdir(parents=True, exist_ok=True)
    icd.write_text(json.dumps({'file_format_version': '1.0.0', 'ICD': {
        'library_path': 'libGLX_nvidia.so.0', 'api_version': '1.3.0'}}, indent=2))
    egl = root / 'share/glvnd/egl_vendor.d/nvidia.json'
    egl.parent.mkdir(parents=True, exist_ok=True)
    egl.write_text(json.dumps({'file_format_version': '1.0.0', 'ICD': {
        'library_path': 'libEGL_nvidia.so.0'}}, indent=2))
    return {'LD_LIBRARY_PATH': ':'.join(directories),
            '__GLX_VENDOR_LIBRARY_NAME': 'nvidia',
            '__EGL_VENDOR_LIBRARY_FILENAMES': str(egl),
            'VK_DRIVER_FILES': str(icd), 'VK_ICD_FILENAMES': str(icd)}, specs


def _gamepads(base, log, shared_root):
    """fake-udev privado, 2 ELF verificados. Nunca sustituye libudev del sistema."""
    _safe_install(['build-essential', 'gcc-multilib', 'libc6-dev-i386',
                   'libudev1:amd64', 'libudev1:i386'], log)
    with tempfile.TemporaryDirectory(prefix='fake-udev-', dir=base) as temporary:
        archive = Path(temporary) / 'selkies.tar.gz'
        _download(f'https://github.com/selkies-project/selkies/archive/refs/tags/{SELKIES_TAG}.tar.gz',
                  archive)
        with tarfile.open(archive) as source:
            # Extraer sólo este addon y rechazar enlaces/path traversal del archivo.
            prefix = f'selkies-{SELKIES_TAG}/addons/fake-udev/'
            members = [member for member in source.getmembers()
                       if member.name.startswith(prefix)]
            if not members:
                raise RuntimeError('El archivo oficial no contiene fake-udev.')
            for member in members:
                if ('..' in Path(member.name).parts or
                        not (member.isfile() or member.isdir())):
                    raise RuntimeError('Entrada de archivo no segura en fake-udev.')
            source.extractall(temporary, members=members, filter='data')
        build = Path(temporary) / prefix
        _run(['make', '-C', str(build), 'all', 'all32'], log=log)
        for arch, triplet in TRIPLETS.items():
            filename = 'libudev.so.1.0.0-fake' if arch == 'amd64' else 'libudev_x86.so.1.0.0-fake'
            source = build / filename
            _elf(source, arch)
            destination = shared_root / 'lib' / triplet
            destination.mkdir(parents=True, exist_ok=True)
            # Reinstalar no debe truncar una biblioteca ya mapeada por un juego.
            staged = destination / 'libudev.so.1.new'
            shutil.copy2(source, staged)
            staged.replace(destination / 'libudev.so.1')
            # La .deb oficial Selkies proporciona ambas variantes del interposer.
            interposer = Path('/usr/lib') / triplet / 'selkies_input_interposer.so'
            _elf(interposer, arch)
    input_directory = Path('/dev/input')
    if not input_directory.exists():
        input_directory.mkdir(mode=0o1777)
        input_directory.chmod(0o1777)
    # $LIB es literal: glibc lo expande según la arquitectura DEL PROCESO.
    library = str(shared_root / '$LIB')
    return {'SELKIES_INTERPOSER': '/usr/$LIB/selkies_input_interposer.so',
            'fake_udev': library + '/libudev.so.1'}


def _quarantine_client(home, base):
    """Reparación solicitada: sólo carpetas redistribuibles, jamás cuentas/juegos."""
    client = home / '.local/share/Steam'
    if client.is_symlink():
        raise RuntimeError('Steam usa un enlace externo; revisar manualmente antes de reparar.')
    quarantine = base / ('quarantine-' + datetime.datetime.now(datetime.timezone.utc)
                         .strftime('%Y%m%dT%H%M%S%fZ'))
    for name in ('ubuntu12_32', 'ubuntu12_64', 'steam.sh'):
        target = client / name
        if target.exists() or target.is_symlink():
            quarantine.mkdir(exist_ok=True)
            target.rename(quarantine / name)
    return str(quarantine) if quarantine.exists() else None


def install_gamepads(session):
    """Mandos opcionales independientes de Steam; no lanza/reinicia procesos."""
    if os.geteuid() != 0:
        raise RuntimeError('La instalación de mandos requiere root; las aplicaciones no.')
    account = pwd.getpwnam(session['user'])
    if account.pw_uid == 0:
        raise ValueError('Los juegos deben ejecutarse como usuario normal.')
    home, runtime = Path(session['home']), Path(session['runtime'])
    if not home.is_absolute() or not runtime.is_absolute() or not home.is_dir() or not runtime.is_dir():
        raise ValueError('Preparar primero home y runtime absolutos del escritorio.')
    shared_root = Path(session.get('fake_udev_root', runtime.parent / 'fake-udev'))
    if not shared_root.is_absolute():
        raise ValueError('fake_udev_root debe ser una ruta absoluta.')
    base = home / '.local/share/pcfree/gamepads'
    _user_directory(base, account)
    log = base / 'install.log'
    _run(['dpkg', '--add-architecture', 'i386'], log=log)
    _run(['apt-get', 'update', '-qq'], log=log)
    preload = _gamepads(base, log, shared_root)
    result = {'installed': True, 'root': str(shared_root), 'log': str(log),
              'source_tag': SELKIES_TAG, 'architectures': list(TRIPLETS),
              'env': {'SELKIES_INTERPOSER': preload['SELKIES_INTERPOSER'],
                      'LD_PRELOAD': preload['SELKIES_INTERPOSER'] + ':' + preload['fake_udev']},
              'unset_env': ['SDL_JOYSTICK_DISABLE_UDEV', 'SDL_JOYSTICK_DEVICE']}
    _owned_write(base / 'installation.json', json.dumps(result, indent=2), account)
    print('Mandos: fake-udev aislado e interposer oficial verificados para 32 y 64 bits.')
    print('Aplicar sólo a aplicaciones/juegos; no precargar en el servidor Selkies.')
    return result


def _launch_script(client, graphics, gamepads, bwrap):
    assignments = ''.join('export ' + key + '=' + shlex.quote(value) + '\n'
                          for key, value in graphics.items() if key != 'LD_LIBRARY_PATH')
    assignments += ('export LD_LIBRARY_PATH=' + shlex.quote(graphics['LD_LIBRARY_PATH']) +
                    '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n')
    if gamepads:
        assignments += 'unset SDL_JOYSTICK_DISABLE_UDEV SDL_JOYSTICK_DEVICE\n'
        # Reusar el input interposer oficial heredado de pcfree-run; copiarlo
        # a otra ruta podría cargar dos instancias de los mismos hooks.
        # No usar expansión shell de $LIB en este valor por defecto.
        assignments += ('if [ -z "${SELKIES_INTERPOSER:-}" ]; then export SELKIES_INTERPOSER=' +
                        shlex.quote(gamepads['SELKIES_INTERPOSER']) + '; fi\n')
        assignments += '''prepend_preload() {
  case ":${LD_PRELOAD:-}:" in *":$1:"*) return;; esac
  LD_PRELOAD="$1${LD_PRELOAD:+:$LD_PRELOAD}"
  export LD_PRELOAD
}
prepend_preload "$SELKIES_INTERPOSER"
'''
        assignments += 'prepend_preload ' + shlex.quote(gamepads['fake_udev']) + '\n'
    if bwrap:
        assignments += 'export BWRAP=' + shlex.quote(bwrap) + '\n'
    return '''#!/bin/sh
set -eu
if [ -r "$HOME/.config/pcfree/game.env" ]; then
  . "$HOME/.config/pcfree/game.env"
fi
if [ "$(id -u)" = 0 ]; then echo 'Steam debe ejecutarse como usuario normal.' >&2; exit 1; fi
: "${HOME:?}" "${XDG_RUNTIME_DIR:?}" "${DISPLAY:?}" "${XAUTHORITY:?}"
bus_ok() {
  dbus-send --bus="$1" --type=method_call --print-reply --dest=org.freedesktop.DBus \
    /org/freedesktop/DBus org.freedesktop.DBus.ListNames >/dev/null 2>&1
}
# Preferir el bus persistente del escritorio. Nunca dbus-run-session alrededor
# del bootstrap: éste puede terminar antes que su steamwebhelper desacoplado.
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] || ! bus_ok "$DBUS_SESSION_BUS_ADDRESS"; then
  address="unix:path=$XDG_RUNTIME_DIR/steam-session-bus"
  (
    flock -x 9
    if ! bus_ok "$address"; then
      dbus-daemon --session --fork --address="$address"
    fi
  ) 9>"$XDG_RUNTIME_DIR/steam-session-bus.lock"
  export DBUS_SESSION_BUS_ADDRESS="$address"
fi
''' + assignments + 'exec ' + shlex.quote(str(client)) + ' "$@"\n'


def _sha512(path):
    digest = hashlib.sha512()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def install_ge_proton(session):
    """Download the pinned GE-Proton release on demand and verify its SHA-512."""
    required = ('user', 'home')
    if any(key not in session for key in required):
        raise ValueError('Estado incompleto para GE-Proton.')
    account = pwd.getpwnam(session['user'])
    home = Path(session['home'])
    base = home / '.cache' / 'pcfree' / 'ge-proton'
    base.mkdir(parents=True, exist_ok=True)
    os.chown(base.parent, account.pw_uid, account.pw_gid)
    os.chown(base, account.pw_uid, account.pw_gid)

    tools = home / '.steam' / 'steam' / 'compatibilitytools.d'
    tools.mkdir(parents=True, exist_ok=True)
    os.chown(tools, account.pw_uid, account.pw_gid)
    target = tools / GE_PROTON_VERSION
    proton = target / 'proton'
    if proton.is_file() and os.access(proton, os.X_OK):
        print(f'GE-Proton ya instalado: {target}')
        return {'installed': True, 'path': str(target), 'version': GE_PROTON_VERSION}

    archive = base / f'{GE_PROTON_VERSION}.tar.gz'
    if not archive.is_file() or _sha512(archive) != GE_PROTON_SHA512:
        if archive.exists():
            archive.unlink()
        print(f'GE-Proton: descargando {GE_PROTON_URL}')
        _download(GE_PROTON_URL, archive)
    if _sha512(archive) != GE_PROTON_SHA512:
        archive.unlink(missing_ok=True)
        raise RuntimeError('El SHA-512 de GE-Proton no coincide con la suma oficial; '
                           'descarga eliminada.')
    extract_dir = base / 'extract'
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts:
                raise RuntimeError('Entrada no segura en el archivo de GE-Proton.')
            if member.issym() or member.islnk():
                link = member.linkname
                if link.startswith('/'):
                    raise RuntimeError('Enlace no seguro en el archivo de GE-Proton.')
                if member.issym():
                    resolved = posixpath.normpath(
                        posixpath.join(posixpath.dirname(member.name), link))
                else:
                    resolved = posixpath.normpath(link)
                if resolved == '..' or resolved.startswith('../') or resolved.startswith('/'):
                    raise RuntimeError('Enlace no seguro en el archivo de GE-Proton.')
                continue
            if not (member.isfile() or member.isdir()):
                raise RuntimeError('Tipo de entrada no admitido en GE-Proton.')
        for member in members:
            source.extract(member, extract_dir)
    roots = [entry for entry in extract_dir.iterdir() if entry.is_dir()]
    if len(roots) != 1:
        raise RuntimeError('El archivo de GE-Proton no tiene una única carpeta raíz.')
    if target.exists():
        shutil.rmtree(target)
    roots[0].rename(target)
    shutil.rmtree(extract_dir, ignore_errors=True)
    archive.unlink(missing_ok=True)
    if not proton.is_file():
        raise RuntimeError('GE-Proton no contiene el ejecutable proton.')
    proton.chmod(0o755)
    for directory, directories, files in os.walk(target):
        os.chown(directory, account.pw_uid, account.pw_gid)
        for name in directories + files:
            os.chown(Path(directory) / name, account.pw_uid, account.pw_gid,
                     follow_symlinks=False)
    result = {'installed': True, 'path': str(target), 'version': GE_PROTON_VERSION,
              'sha512': GE_PROTON_SHA512}
    (base / 'installation.json').write_text(json.dumps(result, indent=2))
    os.chown(base / 'installation.json', account.pw_uid, account.pw_gid)
    print(f'GE-Proton instalado: {target}')
    print('En Steam: Configuración > Compatibilidad > Steam Play para todos los títulos > '
          + GE_PROTON_VERSION)
    return result


def install_steam(session):
    """Instalación explícita opcional, sin lanzar Steam ni modificar el estado global."""
    if os.geteuid() != 0:
        raise RuntimeError('Ejecutar la celda instaladora como root; Steam abrirá como usuario normal.')
    required = ('user', 'home', 'runtime', 'display', 'xauthority', 'gpu_root',
                'driver_version', 'env', 'run_launcher')
    missing = [key for key in required if key not in session]
    if missing:
        raise ValueError('Estado incompleto: ' + ', '.join(missing))
    account = pwd.getpwnam(session['user'])
    if account.pw_uid == 0:
        raise ValueError('El usuario de Steam no puede ser root.')
    home = Path(session['home'])
    runtime = Path(session['runtime'])
    runner = Path(session['run_launcher'])
    if not all(path.is_absolute() for path in (home, runtime, runner, Path(session['gpu_root']))):
        raise ValueError('El estado debe proporcionar rutas absolutas.')
    if not home.is_dir() or not runtime.is_dir() or not os.access(runner, os.X_OK):
        raise RuntimeError('Preparar primero el escritorio y pcfree-run.')
    for key, value in {'HOME': str(home), 'USER': session['user'],
                       'DISPLAY': session['display'], 'XAUTHORITY': session['xauthority'],
                       'XDG_RUNTIME_DIR': str(runtime)}.items():
        if session['env'].get(key) != value:
            raise ValueError(f'Estado y env no coinciden en {key}.')
    driver = session['driver_version']
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', driver):
        raise ValueError('Versión NVIDIA no válida.')
    active = _run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                  env={'LD_LIBRARY_PATH': session['env'].get('LD_LIBRARY_PATH', '')}, host_gpu=True)
    if not active.splitlines() or any(v.strip() != driver for v in active.splitlines()):
        raise RuntimeError('El controlador activo no coincide con session.json; no se cambiará.')
    options = session.get('steam', {})
    if not isinstance(options, dict):
        raise ValueError('session[steam] debe ser un objeto.')
    bwrap = options.get('bwrap')
    if bwrap and (not Path(bwrap).is_absolute() or not os.access(bwrap, os.X_OK)):
        raise ValueError('bwrap debe ser una ruta absoluta a un instalador revisado ya ejecutable.')
    base = home / '.local/share/pcfree/steam'
    _user_directory(base, account)
    log = base / 'install.log'
    _run(['dpkg', '--add-architecture', 'i386'], log=log)
    _run(['apt-get', 'update', '-qq'], log=log)
    packages = ['ca-certificates', 'dbus', 'dbus-x11', 'util-linux',
                'lib32gcc-s1', 'lib32stdc++6']
    # Ubuntu 24.04+ usa libasound2t64; no solicitar el paquete virtual libasound2.
    asound = ('libasound2t64' if _run(['apt-cache', 'search', '^libasound2t64$'])
              else 'libasound2')
    for arch in TRIPLETS:
        packages += [f'{name}:{arch}' for name in (
            'libc6', 'libstdc++6', 'libgcc-s1', 'libgl1', 'libegl1', 'libgles2',
            'libvulkan1', 'libdrm2', 'libx11-6', 'libxext6', 'libxrandr2',
            'libxinerama1', 'libxcursor1', 'libxi6', 'libxss1', 'libxtst6',
            'libxkbcommon-x11-0', 'libudev1', 'libdbus-1-3', 'libpulse0',
            asound, 'libasound2-plugins', 'libfontconfig1', 'libfreetype6')]
    _safe_install(packages, log)
    graphics, specs = _graphics(base, driver, log)
    fake_root = Path(session.get('fake_udev_root', runtime.parent / 'fake-udev'))
    if not fake_root.is_absolute():
        raise ValueError('fake_udev_root debe ser una ruta absoluta.')
    gamepads = _gamepads(base, log, fake_root) if options.get('gamepads', False) else {}
    deb = base / 'steam_latest.deb'
    _download(STEAM_DEB, deb)
    version = _run(['dpkg-deb', '-f', str(deb), 'Version'], log=log)
    if _run(['dpkg-deb', '-f', str(deb), 'Package'], log=log) != 'steam-launcher':
        raise RuntimeError('La descarga oficial no contiene steam-launcher.')
    with tempfile.TemporaryDirectory(prefix='launcher-', dir=base) as temporary:
        extracted = Path(temporary) / 'root'
        _run(['dpkg-deb', '-x', str(deb), str(extracted)], log=log)
        if (not (extracted / 'usr/lib/steam/bin_steam.sh').is_file() or
                not (extracted / 'usr/lib/steam/bootstraplinux_ubuntu12_32.tar.xz').is_file()):
            raise RuntimeError('Cambió el diseño del paquete oficial; revisar el bootstrap.')
        destination = base / 'launcher'
        if destination.exists():
            destination.rename(base / ('launcher-old-' + datetime.datetime.now(datetime.timezone.utc)
                                       .strftime('%Y%m%dT%H%M%S%fZ')))
        extracted.rename(destination)
    quarantine = None
    if options.get('repair_client', False):
        # No terminar procesos de una sesión activa, ni mover archivos en uso.
        running = subprocess.run(['pgrep', '-u', str(account.pw_uid), '-x', 'steam'],
                                 stdout=subprocess.DEVNULL, check=False)
        if running.returncode == 0:
            raise RuntimeError('Cerrar Steam manualmente antes de repair_client; no se ha detenido.')
        quarantine = _quarantine_client(home, base)
    # Su nombre debe ser steam: algunos bootstrap consultan basename($0).
    client = destination / 'usr/lib/steam/steam'
    if not client.exists():
        client.symlink_to('bin_steam.sh')
    launch = base / 'start-steam.sh'
    _owned_write(launch, _launch_script(client, graphics, gamepads, bwrap), account, True)
    command = shlex.join([str(runner), str(launch)])
    wrapper = home / '.local/bin/pcfree-steam'
    _owned_write(wrapper, '#!/bin/sh\nexec ' + command + ' "$@"\n', account, True)
    desktop = '[Desktop Entry]\nType=Application\nName=Steam\nComment=Cliente oficial (inicio manual)\n'
    # Desktop Entry Exec usa comillas dobles, no el quoting de un shell.
    quote = lambda value: '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'
    desktop += ('Exec=' + quote(runner) + ' ' + quote(launch) + '\n'
                'Icon=' + str(destination / 'usr/share/icons/hicolor/256x256/apps/steam.png') + '\n'
                'Terminal=false\nCategories=Game;\n')
    _owned_write(home / '.local/share/applications/pcfree-steam.desktop', desktop, account)
    if (home / 'Desktop').is_dir():
        _owned_write(home / 'Desktop/Steam.desktop', desktop, account, True)
    # El usuario puede abrir desde el menú; no confiar en metadatos GVFS root.
    result = {'installed': True, 'login_validated': False, 'version': version,
              'command': command, 'log': str(log), 'driver_version': driver,
              'nvidia_packages': specs, 'gamepads': bool(gamepads),
              'quarantine': quarantine, 'bwrap': bwrap}
    _owned_write(base / 'installation.json', json.dumps(result, indent=2), account)
    # Todo el árbol privado debe ser modificable por el usuario del cliente.
    for directory, directories, files in os.walk(base):
        os.chown(directory, account.pw_uid, account.pw_gid)
        for name in directories + files:
            os.chown(Path(directory) / name, account.pw_uid, account.pw_gid,
                     follow_symlinks=False)
    print('Steam oficial instalado; no se ha abierto. Abrir Steam desde el menú.')
    print('El primer inicio descarga el cliente. Login y juegos requieren prueba manual.')
    print('Si pressure-vessel rechaza namespaces, revisar proot-bwrap de Selkies; no desactivar seccomp globalmente.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', default='/tmp/pcfree-selkies/session.json')
    parser.add_argument('--gamepads', action='store_true', help='Compilar fake-udev oficial aislado (ambos ELF).')
    parser.add_argument('--gamepads-only', action='store_true', help='Instalar sólo mandos, sin descargar Steam.')
    parser.add_argument('--repair-client', action='store_true', help='Poner sólo binarios redistribuibles en cuarentena.')
    parser.add_argument('--ge-proton', action='store_true', help='Descargar GE-Proton fijado y verificado.')
    args = parser.parse_args()
    session = json.loads(Path(args.session).read_text())
    session['steam'] = dict(session.get('steam', {}))
    if args.ge_proton:
        install_ge_proton(session)
        return
    if args.gamepads:
        session['steam']['gamepads'] = True
    if args.repair_client:
        session['steam']['repair_client'] = True
    if args.gamepads_only:
        install_gamepads(session)
    else:
        install_steam(session)


if __name__ == '__main__':
    main()
