import os, subprocess, urllib.request, tarfile, pwd, time
from pathlib import Path
fb=Path('/tmp/pcfree-firefox'); fb.mkdir(exist_ok=True)
archive=fb/'firefox.tar.xz'
url='https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=es-ES'
if not (fb/'firefox/firefox').exists():
    print('Descargando Firefox oficial...', flush=True)
    urllib.request.urlretrieve(url, archive)
    with tarfile.open(archive) as tf: tf.extractall(fb, filter='data')
    archive.unlink()
user='pcfree-browser'
try: account=pwd.getpwnam(user)
except KeyError:
    subprocess.run(['useradd','--create-home','--home-dir',str(fb/'home'),'--shell','/bin/bash',user],check=True)
    account=pwd.getpwnam(user)
home=Path(account.pw_dir)
home.mkdir(exist_ok=True)
os.chown(home,account.pw_uid,account.pw_gid)
runtime=fb/'runtime'; runtime.mkdir(exist_ok=True); runtime.chmod(0o700)
os.chown(runtime,account.pw_uid,account.pw_gid)
grant=subprocess.run(['xhost','+SI:localuser:'+user],env=desktop_env,capture_output=True,text=True)
print('XAUTH',grant.returncode,grant.stdout,grant.stderr,flush=True)
if grant.returncode: raise RuntimeError('No se pudo autorizar el navegador al escritorio')
browser_env={**desktop_env,'HOME':str(home),'USER':user,'LOGNAME':user,'XDG_RUNTIME_DIR':str(runtime)}
for key in ['DBUS_SESSION_BUS_ADDRESS','SESSION_MANAGER','XAUTHORITY']:
    browser_env.pop(key,None)
log=open(fb/'firefox.log','w')
firefox_process=subprocess.Popen(['runuser','-u',user,'--','dbus-run-session','--',str(fb/'firefox/firefox'),'--no-remote','https://www.minecraft.net/download'],env=browser_env,stdout=log,stderr=subprocess.STDOUT)
time.sleep(12)
print('FIREFOX_PROCESS',firefox_process.pid,firefox_process.poll())
print('FIREFOX_LOG',(fb/'firefox.log').read_text()[-2500:])
if shutil.which('wmctrl'): print(subprocess.run(['wmctrl','-l'],env=desktop_env,capture_output=True,text=True).stdout)
print('FIREFOX_SETUP_DONE; DRIVE_MOUNTED',os.path.ismount('/content/drive'))

import shlex
launcher=Path('/usr/local/bin/pcfree-firefox')
kept={k:browser_env[k] for k in ['DISPLAY','HOME','USER','LOGNAME','XDG_RUNTIME_DIR','LD_LIBRARY_PATH','__GLX_VENDOR_LIBRARY_NAME'] if k in browser_env}
launcher.write_text('#!/bin/sh\nexec runuser -u pcfree-browser -- env '+ ' '.join(shlex.quote(k+'='+v) for k,v in kept.items())+' dbus-run-session -- /tmp/pcfree-firefox/firefox/firefox "$@"\n')
launcher.chmod(0o755)
desk=Path(desktop_env['HOME'])/'Desktop';desk.mkdir(exist_ok=True)
shortcut=desk/'Firefox.desktop'
shortcut.write_text('[Desktop Entry]\nVersion=1.0\nType=Application\nName=Firefox\nExec=/usr/local/bin/pcfree-firefox %u\nIcon=/tmp/pcfree-firefox/firefox/browser/chrome/icons/default/default128.png\nTerminal=false\n')
shortcut.chmod(0o755)
if shutil.which('gio'):subprocess.run(['gio','set',str(shortcut),'metadata::trusted','true'],env=desktop_env,capture_output=True)
subprocess.run(['scrot','--overwrite','/tmp/firefox-check.png'],env=desktop_env,check=True)
display(PILImage.open('/tmp/firefox-check.png'))
print('FIREFOX_SHORTCUT_READY')
