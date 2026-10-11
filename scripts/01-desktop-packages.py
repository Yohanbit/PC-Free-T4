base = Path('/tmp/pcfree-desktop'); base.mkdir(exist_ok=True)
packages = ['xfce4-session', 'xfwm4', 'xfce4-panel', 'xfdesktop4', 'thunar', 'mousepad', 'xfce4-terminal', 'dbus-x11', 'mesa-utils', 'scrot', 'x11-apps', 'x11-xserver-utils', 'xauth', 'xdotool', 'wmctrl', 'curl', 'file', 'lsof', 'zenity', 'xdg-user-dirs']
log = base/'install.log'
with log.open('w') as f:
    subprocess.run(['apt-get', 'update', '-qq'], stdout=f, stderr=subprocess.STDOUT, timeout=240, check=True)
    subprocess.run(['apt-get', 'install', '-y', '--no-install-recommends', *packages], stdout=f, stderr=subprocess.STDOUT, timeout=480, check=True, env={**os.environ, 'DEBIAN_FRONTEND':'noninteractive'})
print('Escritorio instalado desde paquetes de Ubuntu.')
desktop_procs = []
def spawn_desktop(args, name):
    log_handle = (base/(name+'.log')).open('w')
    process = subprocess.Popen(args, env=desktop_env, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True)
    desktop_procs.append(process)
    return process
