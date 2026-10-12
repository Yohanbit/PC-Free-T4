"""Offline scheduling tests; never install software or contact Colab."""
import ast
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
quick = json.loads((root/'PC-Free-T4-Rapido.ipynb').read_text())
env = {}
exec(''.join(quick['cells'][1]['source']), env)
original = env['SOURCES'].copy()
for name, source in original.items():
    assert source == (root/'scripts'/name).read_text()
env['SOURCES'] = {name: 'called.append('+repr(name)+')' for name in original}
env['called'] = []
exec(''.join(quick['cells'][2]['source']), env)
expected = [*env['ORDER'][:5], '07-rustdesk.py']
assert env['called'] == expected
exec(''.join(quick['cells'][4]['source']), env)
assert env['called'] == expected, 'Optional apps ran by default'
env['run_stage']('07-rustdesk.py')
assert env['called'] == expected, 'Repeated stage was not skipped'
try:
    env['run_stage']('06-battly.py')
except AssertionError:
    pass
else:
    raise AssertionError('Battly ran before application-user setup')
env['run_stage']('05-firefox.py')
env['run_stage']('08-steam.py')
assert '06-battly.py' not in env['called'], 'Steam depends on unrelated Battly'
env['SOURCES']['06-battly.py'] = "raise RuntimeError('test failure')"
try:
    env['run_stage']('06-battly.py')
except RuntimeError:
    pass
assert '06-battly.py' not in env['COMPLETED']
for cell in quick['cells']:
    if cell['cell_type'] == 'code':
        ast.parse(''.join(cell['source']))
        assert cell['outputs'] == [] and cell['execution_count'] is None
print('PASS: minimal startup, optional defaults, dependencies, idempotency, failure tracking, clean outputs.')
