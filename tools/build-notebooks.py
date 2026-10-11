"""Regenerate embedded sources after editing scripts; never save runtime output."""
import ast, json, hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'PC-Free-T4.ipynb'
notebook=json.loads(path.read_text())
stages=sorted(p.name for p in (root/'scripts').glob('*.py') if p.name[:2].isdigit() and int(p.name[:2])<=8)
sources={name:(root/'scripts'/name).read_text() for name in [*stages,'09-status.py']}
runner='SOURCES = '+repr(sources)+'\nORDER = '+repr(stages)+'\nCOMPLETED = set()\n'
runner+='''def run_stage(name):
    if name in COMPLETED:
        print('Etapa ya ejecutada en esta sesión:',name)
        return
    index=ORDER.index(name)
    missing=[previous for previous in ORDER[:index] if previous not in COMPLETED]
    assert not missing, 'Completar primero: '+', '.join(missing)
    exec(compile(SOURCES[name],name,'exec'),globals())
    COMPLETED.add(name)
    print('Etapa terminada:',name)
'''
notebook['cells'][1]['source']=runner.splitlines(keepends=True)
notebook['cells'][-3]['source']=(root/'scripts/10-export-worlds.py').read_text().splitlines(keepends=True)
notebook['cells'][-1]['source']=(root/'scripts/11-restore-worlds.py').read_text().splitlines(keepends=True)
for document in [notebook]:
    for index,cell in enumerate(document['cells']):
        cell['id']=hashlib.sha256((str(index)+''.join(cell['source'])).encode()).hexdigest()[:12]
        if cell['cell_type']=='code':
            ast.parse(''.join(cell['source']))
            cell['outputs']=[];cell['execution_count']=None
path.write_text(json.dumps(notebook,ensure_ascii=False,indent=2)+'\n')
backup_path=root/'Drive-Backups.ipynb'
backup=json.loads(backup_path.read_text())
backup['cells'][1]['source']=(root/'scripts/drive-backup-clean.py').read_text().splitlines(keepends=True)
for index,cell in enumerate(backup['cells']):
    cell['id']=hashlib.sha256((str(index)+''.join(cell['source'])).encode()).hexdigest()[:12]
    if cell['cell_type']=='code':
        ast.parse(''.join(cell['source']));cell['outputs']=[];cell['execution_count']=None
backup_path.write_text(json.dumps(backup,ensure_ascii=False,indent=2)+'\n')
print('Cuadernos regenerados sin salidas ni datos de sesión.')
