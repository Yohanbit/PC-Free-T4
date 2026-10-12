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
    # RustDesk needs the desktop, not downloads of Firefox, Battly or Steam.
    prerequisites = {
        '05-firefox.py': ['04-xfce.py'],
        '06-battly.py': ['05-firefox.py'],
        '07-rustdesk.py': ['04-xfce.py'],
        '08-steam.py': ['05-firefox.py'],
    }.get(name, ORDER[:index])
    missing=[previous for previous in prerequisites if previous not in COMPLETED]
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
# Separate fast entry point: one-click startup, apps explicitly opt-in.
def markdown(text):
    return {'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)}
def code(text):
    return {'cell_type':'code','metadata':{},'source':text.splitlines(keepends=True),'outputs':[],'execution_count':None}
quick={key:value for key,value in notebook.items() if key!='cells'}
quick['cells']=[
    markdown('''# PC-Free-T4 — Inicio rápido
Selecciona **GPU T4** y usa **Ejecutar todo** en un entorno nuevo.
Arranca solo **XFCE + aceleración T4 + RustDesk**; no espera Firefox, Battly ni Steam.
Las aplicaciones de abajo son opcionales y están desactivadas por defecto.

Colab gratuito restringe escritorio/control remoto: usa esta receta solo donde el proveedor lo permita.
No evade restricciones, no activa pagos ni monta Drive. GPU y continuidad no garantizadas.
El controlador debe ser 580.82.07; si cambia, detenerse. No reinstalar sobre una sesión activa.
Las credenciales temporales de RustDesk aparecen solo en la salida privada: no guardarlas en GitHub.
'''),
    code(runner),
    code('''# Minimal startup; preserve all hardware/security checks.
import time as _startup_time
_startup_started = _startup_time.monotonic()
for _stage in [*ORDER[:5], '07-rustdesk.py']:
    run_stage(_stage)
print('Escritorio y RustDesk preparados en', round(_startup_time.monotonic()-_startup_started, 1), 'segundos.')
print('Conecta con los datos de RustDesk mostrados arriba. Apps opcionales abajo.')
'''),
    markdown('''## Aplicaciones opcionales — después de conectar
Cambia a `True` solo lo que necesites y ejecuta esta celda.
Battly y Steam requieren el usuario de aplicaciones preparado por Firefox.
La instalación opcional no reinicia ni reconstruye el escritorio.
Para respaldos manuales usa las celdas de exportación/restauración del cuaderno completo.
'''),
    code('''INSTALL_FIREFOX = False
INSTALL_BATTLY = False
INSTALL_STEAM = False
if INSTALL_FIREFOX or INSTALL_BATTLY or INSTALL_STEAM:
    run_stage('05-firefox.py')
if INSTALL_BATTLY:
    run_stage('06-battly.py')
if INSTALL_STEAM:
    run_stage('08-steam.py')
'''),
]
for index,cell in enumerate(quick['cells']):
    cell['id']=hashlib.sha256(('quick-'+str(index)+''.join(cell['source'])).encode()).hexdigest()[:12]
    if cell['cell_type']=='code': ast.parse(''.join(cell['source']))
(root/'PC-Free-T4-Rapido.ipynb').write_text(json.dumps(quick,ensure_ascii=False,indent=2)+'\n')
backup_path=root/'Drive-Backups.ipynb'
backup=json.loads(backup_path.read_text())
backup['cells'][1]['source']=(root/'scripts/drive-backup-clean.py').read_text().splitlines(keepends=True)
for index,cell in enumerate(backup['cells']):
    cell['id']=hashlib.sha256((str(index)+''.join(cell['source'])).encode()).hexdigest()[:12]
    if cell['cell_type']=='code':
        ast.parse(''.join(cell['source']));cell['outputs']=[];cell['execution_count']=None
backup_path.write_text(json.dumps(backup,ensure_ascii=False,indent=2)+'\n')
print('Cuadernos regenerados sin salidas ni datos de sesión.')
