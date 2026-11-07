"""Respaldo automático de sesión al Google Drive.

Sube los archivos de configuración y datos importantes antes de que
la sesión se pierda. Solo toma datos, no ejecuta instalaciones.

Uso: añadir como celda opcional al final del cuaderno.
"""
import shutil
import hashlib
import datetime
from pathlib import Path


def _hash_file(path: Path) -> str:
    """Calcula SHA-256 de un archivo."""
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _backup_file(src: Path, dest: Path) -> None:
    """Copia un archivo y verifica la integridad."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    assert _hash_file(src) == _hash_file(dest), f'Error de integridad: {src}'
    print(f'  OK: {src.relative_to(Path.cwd())}')


def backup_session(drive_folder: Path) -> None:
    """Respalda los archivos de sesión importantes.

    Args:
        drive_folder: Carpeta de destino en Google Drive.
    """
    if not Path('/content/drive').exists():
        print('AVISO: Google Drive no montado.')
        return

    base = Path('/content/drive/MyDrive/PC-Free-T4/sessions')
    base.mkdir(parents=True, exist_ok=True)

    items = [
        (Path.home() / '.config', 'config'),
        (Path.home() / '.local' / 'share', 'local-share'),
        (Path.home() / '.steam' / 'config', 'steam-config'),
        (Path.home() / '.minecraft' / 'saves', 'minecraft-saves'),
        (Path.home() / '.config' / 'pcfree' / 'game.env', 'pcfree-game.env'),
    ]

    session_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    print(f'Sesión: {session_id}')
    print('=== Respaldando configuración y datos ===')

    for src, rel in items:
        if not src.exists():
            print(f'  (omitido: {src} no existe)')
            continue
        if src.is_dir():
            _backup_file(src, session_dir / rel)
        else:
            _backup_file(src, session_dir / src.name)

    minecraft_saves = Path('/home/pcfree-browser/.minecraft/saves')
    if minecraft_saves.exists():
        for world in minecraft_saves.iterdir():
            if (world / 'level.dat').exists():
                world_name = world.name
                dest_world = session_dir / 'saves' / world_name
                dest_world.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(world, dest_world, ignore=shutil.ignore_patterns('session.lock'))
                print(f'  OK: mundo {world.name}')

    print(f'=== Respaldo completado en {session_dir.relative_to(Path.cwd())} ===')


if __name__ == '__main__':
    backup_session(Path('/content/drive/MyDrive/PC-Free-T4'))
