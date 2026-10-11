import os, subprocess, shutil, secrets, time, shlex, pwd, tarfile, urllib.request
from pathlib import Path
from IPython.display import display
from PIL import Image as PILImage

assert os.geteuid() == 0, 'Esta configuración experimental requiere el entorno Linux administrado de la prueba.'
assert not os.path.ismount('/content/drive'), 'Desmonta Drive antes de ejecutar este instalador experimental.'
r = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version', '--format=csv,noheader'], capture_output=True, text=True, check=True)
name, driver_version = [x.strip() for x in r.stdout.strip().split(',')]
print('GPU:', name, '| Controlador:', driver_version)
assert 'T4' in name, 'Esta receta solo fue comprobada con Tesla T4.'
assert driver_version == '580.82.07', 'El controlador cambió. Revisar paquetes NVIDIA antes de continuar; no forzar otra versión.'
assert shutil.disk_usage('/tmp').free > 8 * 1024**3, 'Se requieren al menos 8 GiB libres para la preparación; Minecraft puede necesitar más.'
assert not Path('/tmp/.X11-unix/X98').exists(), 'Ya existe el escritorio :98. No reinstales encima ni reinicies la máquina; usa el entorno activo.'
print('Comprobaciones terminadas. Sin Drive, pagos ni medidas para evitar cortes de sesión.')
