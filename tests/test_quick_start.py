"""Offline notebook scheduling; never install software or contact Colab."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
notebook = json.loads((root / 'PC-Free-T4.ipynb').read_text(encoding='utf-8'))
code_cells = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code']

# Verify all code cells have clean outputs
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        assert cell['outputs'] == [] and cell['execution_count'] is None

print('PASS: notebook structure and clean outputs verified.')
