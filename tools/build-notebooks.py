"""Deterministic standalone notebook builder; never retain runtime outputs.

Owned desktop notebooks only. Drive-Backups.ipynb remains untouched; legacy
world backup sources are embedded in disabled manual cells of the full notebook.
Run this again after updating either optional compatibility source.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def markdown(text):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': text.splitlines(keepends=True)}


def code(text):
    ast.parse(text)
    return {'cell_type': 'code', 'metadata': {}, 'source': text.splitlines(keepends=True),
            'outputs': [], 'execution_count': None}


def embedded_sources():
    sources = {}
    for name in ('selkies-desktop.py', 'compat-steam.py', 'compat-apps.py',
                 '10-export-worlds.py', '11-restore-worlds.py'):
        path = ROOT / 'scripts' / name
        if path.exists():
            sources[name] = path.read_text()
        elif name.startswith('compat-'):
            # No runtime download dependency. Unavailable option fails explicitly.
            sources[name] = 'raise RuntimeError("Fuente opcional no integrada; regenerar cuadernos con tools/build-notebooks.py.")\n'
            print('AVISO: falta', name, '— regenerar cuando esté listo.')
        else:
            raise FileNotFoundError(path)
        ast.parse(sources[name], filename=name)
    return sources


def build():
    sources = embedded_sources()
    runner = 'SOURCES = ' + repr(sources) + '\n'
    runner += '''# Fuentes integradas: no clonar el repositorio ni ejecutar notebooks anteriores.
import os, pwd, shutil
from pathlib import Path
_core = {'__name__': 'pcfree_core'}
exec(compile(SOURCES['selkies-desktop.py'], 'selkies-desktop.py', 'exec'), _core)
def optional_module(name):
    namespace = {'__name__': 'pcfree_optional'}
    exec(compile(SOURCES[name], name, 'exec'), namespace)
    return namespace
'''
    intro = '''Selecciona **Entorno de ejecución → GPU T4** y usa **Ejecutar todo** en una VM nueva.
Perfil gaming: **T4 + XFCE 720p + Selkies/NVENC H.264 + Turbo + 60 FPS objetivo + CBR 5 Mbps**.
**Flatpak/Sober activados**: preparación en segundo plano tras publicar el acceso,
condicionada al sandbox real. En la VM de desarrollo Colab bloqueó el montaje de `/proc`.
Firefox con EGL NVIDIA/WebRender se descarga en segundo plano; terminal, archivos, descargas e instalador de paquetes
Ubuntu están preparados. **No se abre ninguna aplicación automáticamente.**

Colab administrado restringe escritorio/control remoto: utiliza esto solo donde el proveedor
lo permita. No evita restricciones ni mantiene sesiones vivas, no monta Drive ni activa pagos.
La GPU, continuidad, compatibilidad de juegos y anticheat no están garantizados.
Las bibliotecas NVIDIA deben coincidir exactamente con el kernel y existir en los archivos
oficiales Ubuntu o el repositorio CUDA NVIDIA para Ubuntu 24.04 amd64; si no, se detiene
sin cambiar el controlador. No reejecutar sobre otro escritorio.

El enlace y la contraseña son privados, temporales y nuevos por sesión. **No guardar ni
compartir salidas del cuaderno**. El túnel expone una pantalla autenticada en Internet;
cerrar la VM al terminar. Pulsar **Jugar** en la web para solicitar captura del ratón y teclado.
FPS y bitrate son ajustables; rendimiento y latencia no garantizados.
'''
    start = '''# @title Iniciar escritorio mínimo (no abre ventanas)
DOWNLOAD_FIREFOX = True # @param {type:"boolean"}
FRAMERATE = 60 # @param {type:"integer"}
VIDEO_BITRATE_KBPS = 5000 # @param {type:"integer"}
INSTALL_ROBLOX = True # @param {type:"boolean"}
SESSION = _core['bootstrap'](firefox=DOWNLOAD_FIREFOX, framerate=FRAMERATE, bitrate=VIDEO_BITRATE_KBPS)
browser_env = SESSION['env']  # Solo compatibilidad con respaldos manuales existentes.
_apps = optional_module('compat-apps.py')
_sober_task = _apps['roblox_background'](SESSION) if INSTALL_ROBLOX else None
'''
    steam = '''# @title Steam opcional — instala, no inicia el cliente
INSTALL_STEAM = False # @param {type:"boolean"}
STEAM_GAMEPADS = False # @param {type:"boolean"}
INSTALL_GAMEPADS = False # @param {type:"boolean"}
if (INSTALL_STEAM or INSTALL_GAMEPADS) and _sober_task is not None:
    _sober_task.join()  # Serializar APT con la descarga inicial de Sober.
if INSTALL_STEAM:
    SESSION['steam'] = {'gamepads': STEAM_GAMEPADS}
    optional_module('compat-steam.py')['install_steam'](SESSION)
if INSTALL_GAMEPADS and not (INSTALL_STEAM and STEAM_GAMEPADS):
    optional_module('compat-steam.py')['install_gamepads'](SESSION)
'''
    apps = '''# @title Aplicaciones opcionales — todo desactivado en Ejecutar todo
INSTALL_WINE = False # @param {type:"boolean"}
INSTALL_PRISM_MINECRAFT = False # @param {type:"boolean"}
INSTALL_LUTRIS = False # @param {type:"boolean"}
INSTALL_HEROIC = False # @param {type:"boolean"}
INSTALL_JAVA = False # @param {type:"boolean"}
INSTALL_GAMING_LIBS = False # @param {type:"boolean"}
INSTALL_DEB_INSTALLER = False # @param {type:"boolean"}
INSTALL_BLENDER = False # @param {type:"boolean"}
INSTALL_GODOT = False # @param {type:"boolean"}
INSTALL_VINEGAR = False # @param {type:"boolean"}
_options = {'wine': INSTALL_WINE, 'prism': INSTALL_PRISM_MINECRAFT,
            'lutris': INSTALL_LUTRIS, 'heroic': INSTALL_HEROIC,
            'java': INSTALL_JAVA, 'gaming-libs': INSTALL_GAMING_LIBS,
            'deb-installer': INSTALL_DEB_INSTALLER, 'blender': INSTALL_BLENDER,
            'godot': INSTALL_GODOT, 'vinegar': INSTALL_VINEGAR}
if any(_options.values()):
    if _sober_task is not None:
        _sober_task.join()
    for _option, _enabled in _options.items():
        if _enabled:
            _apps['install_app'](_option, SESSION)
'''
    common = [markdown(intro), code(runner), code(start),
              markdown('''## Opcionales — después de conectar
Cambia únicamente las opciones necesarias a `True` y ejecuta su celda.
Steam/Wine y juegos pueden necesitar dependencias de 32 bits y ajustes específicos.
El mapa de compatibilidad informa opciones no soportadas; no se fuerza Flatpak privilegiado.
Los mandos requieren `pcfree-run programa [argumentos]` y bibliotecas por arquitectura;
Steam ofrece fake-udev opcional. No se promete compatibilidad total de mandos o juegos.
`INSTALL_GAMEPADS` prepara mandos independientemente, sin descargar Steam.
Vinegar/Roblox Studio es experimental: instalación no equivale a ejecución validada.
Sober se incluye por defecto; `INSTALL_ROBLOX` en la celda de inicio permite desactivarlo.
Comprueba CPU x86-64, SSE4.1, kernel >=5.11 y el sandbox de namespaces de usuario.
Instala Flatpak y, cuando el sandbox lo permite, Sober y la extensión NVIDIA exacta.
No desactiva el sandbox ni cambia el controlador.
El sandbox Bubblewrap con `/proc` se prueba antes de descargar runtimes; en la VM
de desarrollo Colab rechazó ese montaje, por lo que Roblox no pudo ejecutarse.
SSE4.2 y Vulkan >=1.1 son recomendados; SSE4.1 no se instala por software.
Si la VM no cumple requisitos, conserva el escritorio y muestra un diagnóstico.
Roblox sigue siendo experimental: descarga el juego al abrir Sober por primera vez.
Usa también `pcfree-run /ruta/al/juego [argumentos]` para juegos descargados.
Chrome/Chromium reciente recomendado: mandos, fullscreen y pointer lock dependen del
navegador/dispositivo; Android y otros navegadores no ofrecen todas las funciones.
Para apuntar: activar **Gaming mode** y capturar el ratón dentro del escritorio.
Consultar la sección de controles del README antes de jugar desde Android.
'''), code(steam), code(apps),
              markdown('''## Estado y diagnóstico
Credenciales: salida privada de inicio; archivos locales separados en
`/tmp/pcfree-selkies/access.json` (0600). Contrato sin credenciales: `session.json`.
Registros por servicio en `/tmp/pcfree-selkies/`. Firefox informa éxito/error en la salida
y en `firefox-status.txt`; para reintentar una descarga fallida usa
`_core['firefox_background'](SESSION)`. Repetir el inicio no reinicia servicios activos;
Sober: consultar `sober-status.txt` e `install-roblox.log`; reintentar con
`_apps['roblox_background'](SESSION)` sin reiniciar el escritorio.
si hay un arranque parcial, inspecciona registros y usa una VM nueva.
''')]
    for filename, title, full in [('PC-Free-T4.ipynb', 'PC-Free-T4', True),
                                 ('PC-Free-T4-Rapido.ipynb', 'PC-Free-T4 — Inicio rápido', False)]:
        cells = [markdown('# ' + title + '\n' + intro), *common[1:]]
        if full:
            cells += [markdown('''## Respaldos manuales separados — desactivados
Solo mundos Minecraft, no cuentas/perfiles/contraseñas. Primero guardar y cerrar el juego.
Para exportar: activar la celda, inspeccionar índices y editar la selección dentro de ella.
Para restaurar: activar y definir una carpeta `saves` dentro del home de aplicaciones.
No se monta Drive. El cuaderno independiente **Drive-Backups.ipynb** conserva el flujo
manual de Drive, sin unirlo al arranque del escritorio.
''')]
            for name, toggle in [('10-export-worlds.py', 'EXPORT_WORLDS'),
                                 ('11-restore-worlds.py', 'RESTORE_WORLDS')]:
                # Editable embedded code, gated so Run All does not scan/upload/download.
                cells.append(code(f'{toggle} = False\nif {toggle}:\n' +
                                  ''.join('    ' + line + '\n' for line in sources[name].splitlines())))
        notebook = dict(nbformat=4, nbformat_minor=5,
                        metadata={'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                                  'language_info': {'name': 'python'},
                                  'colab': {'name': filename, 'provenance': []}, 'accelerator': 'GPU'}, cells=cells)
        for index, cell in enumerate(cells):
            cell['id'] = hashlib.sha256((filename + str(index) + ''.join(cell['source'])).encode()).hexdigest()[:12]
        (ROOT / filename).write_text(json.dumps(notebook, ensure_ascii=False, indent=2) + '\n')
    print('Cuadernos Selkies regenerados sin salidas, credenciales ni dependencias de clonación.')


if __name__ == '__main__':
    build()
