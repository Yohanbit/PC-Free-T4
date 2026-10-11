import os, subprocess, time, urllib.request
from pathlib import Path
print('RUSTDESK_PREFLIGHT')
assert not os.path.ismount('/content/drive'), 'Drive debe permanecer desconectado'
assert 'desktop_env' in globals(), 'El entorno grafico ya no esta disponible'
r = subprocess.run(['xrandr'], env=desktop_env, capture_output=True, text=True)
assert r.returncode == 0, 'La pantalla grafica no responde'
print('DISPLAY_ALIVE', desktop_env.get('DISPLAY'))
rd_base = Path('/tmp/pcfree-rustdesk'); rd_base.mkdir(exist_ok=True)
rd_deb = rd_base/'rustdesk.deb'
url = 'https://github.com/rustdesk/rustdesk/releases/download/1.4.4/rustdesk-1.4.4-x86_64.deb'
urllib.request.urlretrieve(url, rd_deb)
print('OFFICIAL_PACKAGE_BYTES', rd_deb.stat().st_size)
print('PACKAGE', subprocess.check_output(['dpkg-deb','-f',str(rd_deb),'Package','Version','Depends'],text=True))
rd_root = rd_base/'root'
subprocess.run(['dpkg-deb','-x',str(rd_deb),str(rd_root)],check=True)
rd_bin = rd_root/'usr/share/rustdesk/rustdesk'
rd_env = {**desktop_env, 'LD_LIBRARY_PATH':str(rd_bin.parent/'lib')+':'+desktop_env.get('LD_LIBRARY_PATH','')}
deps = ['libgstreamer-plugins-base1.0-0','libxdo3','libva2','libva-drm2','libva-x11-2','libayatana-appindicator3-1']
with (rd_base/'deps.log').open('w') as log:
    subprocess.run(['apt-get','install','-y','--no-install-recommends',*deps],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'},check=True)
print('VERSION', subprocess.run([str(rd_bin),'--version'],env=rd_env,capture_output=True,text=True,timeout=20))
# Execute only once; do not repeat while these processes remain active.
rd_server = subprocess.Popen([str(rd_bin),'--server'],env=rd_env,cwd=str(rd_bin.parent),stdout=(rd_base/'server.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
rd_gui = subprocess.Popen(['dbus-run-session','--',str(rd_bin)],env=rd_env,cwd=str(rd_bin.parent),stdout=(rd_base/'gui.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
time.sleep(8)
print('RUSTDESK_STATUS',rd_server.poll(),rd_gui.poll())
print('ID',subprocess.run([str(rd_bin),'--get-id'],env=rd_env,capture_output=True,text=True,timeout=15).stdout.strip())
subprocess.run(['scrot','--overwrite',str(rd_base/'screen.png')],env=desktop_env,check=True)
from PIL import Image as PILImage
display(PILImage.open(rd_base/'screen.png'))
