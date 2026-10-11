assert gpu_xorg.poll() is None, 'Xorg no sigue activo. Revisar registros; no borrar archivos.'
gpu_home=gpu_root/'home'; gpu_home.mkdir(exist_ok=True)
gpu_runtime=gpu_root/'runtime'; gpu_runtime.mkdir(exist_ok=True); gpu_runtime.chmod(0o700)
desktop_env={**gpu_env, 'HOME':str(gpu_home), 'XDG_RUNTIME_DIR':str(gpu_runtime)}
for key in ['SESSION_MANAGER','DBUS_SESSION_BUS_ADDRESS']:
    desktop_env.pop(key,None)
(gpu_home/'Desktop').mkdir(exist_ok=True)
spawn_desktop(['dbus-run-session','--','xfce4-session'],'xfce-t4')
time.sleep(8)
r=subprocess.run(['xrandr','--output','DVI-D-0','--mode','1280x720','--pos','0x0'], env=desktop_env, capture_output=True, text=True)
if r.returncode:
    print('No se pudo ajustar DVI-D-0 automáticamente:',r.stderr)
gl=subprocess.run(['glxinfo','-B'],env=desktop_env,capture_output=True,text=True,check=True).stdout
print(gl)
assert 'NVIDIA' in gl and 'Tesla T4' in gl, 'No se confirmó renderizado T4; detener la prueba.'
subprocess.run(['scrot','--overwrite',str(base/'desktop.png')],env=desktop_env,check=True)
display(PILImage.open(base/'desktop.png'))
