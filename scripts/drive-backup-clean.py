# Run ONLY in a separate fresh CPU notebook, never in the desktop runtime.
import os, shutil, zipfile, json, hashlib
from pathlib import Path
from google.colab import files, drive

assert not Path('/tmp/.X11-unix/X98').exists(), 'No conectar Drive al entorno de escritorio.'
assert not any(Path('/tmp',name).exists() for name in ['pcfree-battly','pcfree-rustdesk','pcfree-steam']), 'Usar un entorno limpio separado.'
print('Subir el ZIP de mundos descargado desde la máquina, no carpetas de cuentas.')
uploaded=files.upload()
assert len(uploaded)==1
name=next(iter(uploaded))
source=Path(name)
assert source.name==name and source.suffix.lower()=='.zip'
with zipfile.ZipFile(source) as archive:
    assert archive.getinfo('manifest.json').file_size<=10*1024**2
    manifest=json.loads(archive.read('manifest.json'))
    assert manifest.get('format')=='pc-free-worlds-v1', 'No es un respaldo de mundos de este proyecto.'
# Google asks the user for authorization. No third-party desktop apps here.
drive.mount('/content/drive')
try:
    folder=Path('/content/drive/MyDrive/PC-Free-Backups')
    folder.mkdir(parents=True,exist_ok=True)
    destination=folder/source.name
    assert not destination.exists(), 'Ya existe un respaldo con este nombre; no sobrescribir.'
    shutil.copyfile(source,destination)
    assert hashlib.file_digest(source.open('rb'),'sha256').hexdigest()==hashlib.file_digest(destination.open('rb'),'sha256').hexdigest()
    print('Respaldo copiado y verificado en MyDrive/PC-Free-Backups/',source.name)
finally:
    drive.flush_and_unmount()
    print('Drive desmontado. No ejecutar apps de terceros en este cuaderno.')
