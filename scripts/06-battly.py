# Run inside the existing Colab runtime; not in the agent sandbox.
import urllib.request, hashlib, tarfile, os
from pathlib import Path
battly_base=Path('/tmp/pcfree-battly'); battly_base.mkdir(exist_ok=True)
battly_archive=battly_base/'battly.tar.gz'
battly_url='https://github.com/BattlyLauncher/battlylauncher/releases/download/3.0.1/Battly-Launcher-linux-x64.tar.gz'
battly_sha='547a282d28020b71b14a486f25e7190a3e1ff38fb89963e6c8af08a905b51a01'
print('Descargando Battly 3.0.1 oficial...',flush=True)
urllib.request.urlretrieve(battly_url,battly_archive)
actual=hashlib.file_digest(battly_archive.open('rb'),'sha256').hexdigest()
assert actual==battly_sha,'SHA256 no coincide; no ejecutar'
print('SHA256 correcto',flush=True)
battly_root=battly_base/'app';battly_root.mkdir(exist_ok=True)
with tarfile.open(battly_archive) as tf:tf.extractall(battly_root,filter='data')
battly_archive.unlink()
print('Archivos principales:',[(str(p.relative_to(battly_root)),oct(p.stat().st_mode&0o777)) for p in battly_root.iterdir()])
print('Ejecutables:',[str(p) for p in battly_root.rglob('*') if p.is_file() and os.access(p,os.X_OK)][:35])
print('BATTLY_DOWNLOAD_COMPLETE')
import shlex, subprocess, time
battly_bin=next(battly_root.rglob('battlylauncher'))
print('DEPENDENCIAS',subprocess.getoutput('ldd '+shlex.quote(str(battly_bin))))
sandbox=battly_bin.parent/'chrome-sandbox'
if sandbox.exists():
    os.chown(sandbox,0,0)
    sandbox.chmod(0o4755)
bl=Path('/usr/local/bin/pcfree-battly')
kept={k:browser_env[k] for k in ['DISPLAY','HOME','USER','LOGNAME','XDG_RUNTIME_DIR','LD_LIBRARY_PATH','__GLX_VENDOR_LIBRARY_NAME'] if k in browser_env}
bl.write_text('#!/bin/sh\nexec runuser -u pcfree-browser -- env '+ ' '.join(shlex.quote(k+'='+v) for k,v in kept.items())+' dbus-run-session -- '+shlex.quote(str(battly_bin))+' "$@"\n')
bl.chmod(0o755)
icons=list((battly_bin.parent/'resources/app').rglob('icon.png'))
icon=str(icons[0]) if icons else 'applications-games'
shortcut=Path(desktop_env['HOME'])/'Desktop/Battly.desktop'
shortcut.write_text('[Desktop Entry]\nVersion=1.0\nType=Application\nName=Battly Launcher\nExec=/usr/local/bin/pcfree-battly\nIcon='+icon+'\nTerminal=false\nCategories=Game;\n')
shortcut.chmod(0o755)
subprocess.run(['gio','set',str(shortcut),'metadata::trusted','true'],env=desktop_env,capture_output=True)
battly_log=open(battly_base/'battly.log','w')
battly_process=subprocess.Popen([str(bl)],env=desktop_env,stdout=battly_log,stderr=subprocess.STDOUT)
time.sleep(10)
print('BATTLY_PROCESS',battly_process.pid,battly_process.poll())
print('BATTLY_LOG',(battly_base/'battly.log').read_text()[-2500:])
subprocess.run(['scrot','--overwrite','/tmp/battly-check.png'],env=desktop_env,check=True)
display(PILImage.open('/tmp/battly-check.png'))
print('BATTLY_SHORTCUT_DONE')

appdir=battly_bin.parent/'resources/app'
# Run in the existing Colab runtime after battly-setup.py.
# TAR Linux build: AppImage updater returns without event, leaving splash stuck.
import signal, time
source=appdir/'src/app.js'
backup=source.with_suffix('.js.original')
if not backup.exists():backup.write_bytes(source.read_bytes())
text=source.read_text()
old='if (dev || !app.isPackaged) {'
new='if (dev || !app.isPackaged || (process.platform === "linux" && !process.env.APPIMAGE)) {'
if old in text:
    assert text.count(old)==1
    source.write_text(text.replace(old,new,1))
else:
    assert new in text,'Unexpected updater code; do not patch blindly'
for d in Path('/proc').iterdir():
    if not d.name.isdigit():continue
    try:
        if os.path.realpath(str(d/'exe'))==str(battly_bin):os.kill(int(d.name),signal.SIGTERM)
    except (OSError,ProcessLookupError):pass
time.sleep(3)
battly_log=open(battly_base/'battly-fixed.log','w')
battly_process=subprocess.Popen([str(bl)],env=desktop_env,stdout=battly_log,stderr=subprocess.STDOUT)
time.sleep(15)
print('BATTLY_PATCH_PROCESS',battly_process.pid,battly_process.poll())
print((battly_base/'battly-fixed.log').read_text()[-3500:])
subprocess.run(['scrot','--overwrite','/tmp/battly-fixed.png'],env=desktop_env,check=True)
display(PILImage.open('/tmp/battly-fixed.png'))
print('BATTLY_PATCH_CHECK_DONE')
