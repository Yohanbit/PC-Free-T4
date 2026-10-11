# Prueba Xorg local: sin puertos de red y sin sustituir el escritorio CPU.
root=gpu_root/'root'
libdirs=sorted({str(p.parent) for p in root.rglob('*.so*') if p.is_file()})
gpu_env={**os.environ,'LD_LIBRARY_PATH':':'.join(libdirs)+':'+os.environ.get('LD_LIBRARY_PATH',''),'DISPLAY':':98','__GLX_VENDOR_LIBRARY_NAME':'nvidia'}
driver=next(root.rglob('nvidia_drv.so'))
module_path=str(driver.parent.parent)+',/usr/lib/xorg/modules'
bus=subprocess.check_output(['nvidia-smi','--query-gpu=pci.bus_id','--format=csv,noheader'],text=True).strip()
parts=bus.split(':'); bdf=parts[-1].split('.')
busid='PCI:'+str(int(parts[-2],16))+':'+str(int(bdf[0],16))+':'+str(int(bdf[1],16))
conf=gpu_root/'xorg.conf'
conf.write_text('''Section "ServerFlags"
 Option "AutoAddDevices" "false"
 Option "AutoAddGPU" "false"
EndSection
Section "Device"
 Identifier "T4"
 Driver "nvidia"
 Option "AllowEmptyInitialConfiguration" "true"
EndSection
Section "Screen"
 Identifier "GPU-Screen"
 Device "T4"
 DefaultDepth 24
 SubSection "Display"
  Depth 24
  Virtual 1280 720
 EndSubSection
EndSection
''')
conf.write_text(conf.read_text().replace(' Driver "nvidia"',' Driver "nvidia"\n BusID "'+busid+'"'))
authority=gpu_root/'.Xauthority'
authority.touch(mode=0o600,exist_ok=True)
authority.chmod(0o600)
subprocess.run(['xauth','-f',str(authority),'add',':98','MIT-MAGIC-COOKIE-1',secrets.token_hex(16)],check=True)
gpu_env['XAUTHORITY']=str(authority)
gpu_xorg=subprocess.Popen(['/usr/lib/xorg/Xorg',':98','-config',str(conf),'-modulepath',module_path,'-logfile',str(gpu_root/'Xorg.log'),'-nolisten','tcp','-noreset','-novtswitch','-sharevts','-auth',str(authority)],env=gpu_env,stdout=(gpu_root/'xorg-stdout.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
time.sleep(7)
print('XORG_STATUS',gpu_xorg.poll())
print('XORG_LOG',(gpu_root/'Xorg.log').read_text()[-11000:] if (gpu_root/'Xorg.log').exists() else (gpu_root/'xorg-stdout.log').read_text())
r=subprocess.run(['glxinfo','-B'],env=gpu_env,capture_output=True,text=True,timeout=30)
print('T4_OPENGL_RESULT',r.returncode,r.stdout,r.stderr)

assert gpu_xorg.poll() is None, 'Xorg no inició; revisar registros.'
assert r.returncode==0 and 'Tesla T4' in r.stdout, 'OpenGL T4 no confirmado.'
