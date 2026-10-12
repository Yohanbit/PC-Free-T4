"""Offline notebook scheduling; never install software or contact Colab."""
import ast
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for filename in ('PC-Free-T4.ipynb', 'PC-Free-T4-Rapido.ipynb'):
    notebook = json.loads((root / filename).read_text())
    code = [cell for cell in notebook['cells'] if cell['cell_type'] == 'code']
    runner = ast.parse(''.join(code[0]['source']))
    embedded = ast.literal_eval(runner.body[0].value)
    assert {'selkies-desktop.py', 'compat-steam.py', 'compat-apps.py'} <= set(embedded)
    for name, source in embedded.items():
        assert source == (root / 'scripts' / name).read_text()
    events = []
    env = {'_core': {'bootstrap': lambda **args: events.append(('core', args)) or {'env': {}}},
           'optional_module': lambda name: {'roblox_background': lambda session: events.append(('sober-background', session))}}
    for cell in code[1:]:
        source = ''.join(cell['source'])
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and (target.id.startswith('INSTALL_') or target.id == 'STEAM_GAMEPADS'):
                        assert isinstance(node.value, ast.Constant) and node.value.value is (target.id == 'INSTALL_ROBLOX')
        exec(compile(tree, filename, 'exec'), env)
    assert len(events) == 2 and events[0][0] == 'core' and events[1][0] == 'sober-background'
    assert events[0][1]['firefox'] is True
    assert events[0][1]['framerate'] == 60 and events[0][1]['bitrate'] == 5000
    for cell in code:
        assert cell['outputs'] == [] and cell['execution_count'] is None
print('PASS: standalone entrypoints, desktop before background Sober, optional defaults, background Firefox, clean outputs.')
