"""Standalone notebook synchronizer for PC-Free-T4.ipynb.
Extracts internal scripts from PC-Free-T4.ipynb cell 2 into scripts/
and verifies notebook structure.
"""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    nb_path = ROOT / 'PC-Free-T4.ipynb'
    if not nb_path.exists():
        raise FileNotFoundError(nb_path)

    notebook = json.loads(nb_path.read_text(encoding='utf-8'))
    cell2 = ''.join(notebook['cells'][2]['source'])
    namespace = {}
    exec(compile(cell2, 'cell2', 'exec'), namespace)
    sources = namespace.get('SOURCES', {})

    for name, content in sources.items():
        script_path = ROOT / 'scripts' / name
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(content, encoding='utf-8')
        ast.parse(content, filename=name)

    print('Fuentes actualizadas desde PC-Free-T4.ipynb.')


if __name__ == '__main__':
    build()
