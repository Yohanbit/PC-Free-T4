assert 'browser_env' in globals(), 'Preparar primero el usuario de aplicaciones con Firefox.'
steam_base=Path('/tmp/pcfree-steam'); steam_base.mkdir(exist_ok=True)
steam_deb=steam_base/'steam.deb'
urllib.request.urlretrieve('https://repo.steampowered.com/steam/archive/stable/steam_latest.deb',steam_deb)
print(subprocess.run(['dpkg-deb','-f',str(steam_deb),'Version'],capture_output=True,text=True,check=True).stdout)
steam_root=steam_base/'root';steam_root.mkdir(exist_ok=True)
subprocess.run(['dpkg-deb','-x',str(steam_deb),str(steam_root)],check=True)
subprocess.run(['dpkg','--add-architecture','i386'],check=True)
log=steam_base/'libraries.log'
with log.open('w') as f:
    subprocess.run(['apt-get','update','-qq'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=240)
    subprocess.run(['apt-get','install','-y','--no-install-recommends','lib32gcc-s1','lib32stdc++6','libgl1:i386','libdrm2:i386'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=480,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'})
# Official launcher supports running directly beside its bootstrap tarball.
# Dependencies are handled above; no interactive package helper is necessary.
steam_script=steam_root/'usr/lib/steam/bin_steam.sh'
assert steam_script.exists()
kept={k:browser_env[k] for k in ['DISPLAY','HOME','USER','LOGNAME','XDG_RUNTIME_DIR','LD_LIBRARY_PATH','__GLX_VENDOR_LIBRARY_NAME'] if k in browser_env}
steam_wrapper=Path('/usr/local/bin/pcfree-steam')
steam_wrapper.write_text('#!/bin/sh\nexec runuser -u pcfree-browser -- env '+' '.join(shlex.quote(k+'='+v) for k,v in kept.items())+' dbus-run-session -- '+shlex.quote(str(steam_script))+' "$@"\n')
steam_wrapper.chmod(0o755)
shortcut=Path(desktop_env['HOME'])/'Desktop/Steam.desktop'
shortcut.write_text('[Desktop Entry]\nVersion=1.0\nType=Application\nName=Steam\nExec=/usr/local/bin/pcfree-steam\nIcon='+str(steam_root/'usr/share/icons/hicolor/256x256/apps/steam.png')+'\nTerminal=false\nCategories=Game;\n')
shortcut.chmod(0o755)
subprocess.run(['gio','set',str(shortcut),'metadata::trusted','true'],env=desktop_env,capture_output=True)
steam_process=subprocess.Popen([str(steam_wrapper)],env=desktop_env,stdout=(steam_base/'steam.log').open('w'),stderr=subprocess.STDOUT)
print('Steam solicitado. La primera actualización puede tardar varios minutos.')
print('Iniciar sesión manualmente desde RustDesk, sin enviar contraseñas al chat. Steam Link aún no validado.')
