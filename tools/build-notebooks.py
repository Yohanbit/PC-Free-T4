"""Standalone notebook synchronizer for PC-Free-T4.ipynb.
Extracts internal scripts from the kernel cell of PC-Free-T4.ipynb into scripts/
and verifies notebook structure.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KERNEL_TITLE = 'Cargar núcleo interno'


def kernel_source(notebook):
    """Localiza la celda del núcleo por su título, nunca por posición."""
    for cell in notebook['cells']:
        source = ''.join(cell['source'])
        if KERNEL_TITLE in source:
            return source
    raise AssertionError('No se encontró la celda del núcleo: ' + KERNEL_TITLE)


def embedded_sources(source):
    """Lee SOURCES con el árbol de sintaxis: no ejecuta la celda ni sus efectos."""
    for node in ast.parse(source).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == 'SOURCES'):
            return ast.literal_eval(node.value)
    raise AssertionError('La celda del núcleo no define SOURCES como literal.')


def build():
    nb_path = ROOT / 'PC-Free-T4.ipynb'
    if not nb_path.exists():
        raise FileNotFoundError(nb_path)

    notebook = json.loads(nb_path.read_text(encoding='utf-8'))
    sources = embedded_sources(kernel_source(notebook))

    for name, content in sources.items():
        script_path = ROOT / 'scripts' / name
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(content, encoding='utf-8')
        ast.parse(content, filename=name)

    print('Fuentes actualizadas desde PC-Free-T4.ipynb.')


if __name__ == '__main__':
    build()
