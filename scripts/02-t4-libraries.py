# Ejecutar en el cuaderno Colab: bibliotecas aisladas, sin cambiar el controlador del kernel.
import subprocess, os, glob, time
from pathlib import Path
gpu_root=Path('/tmp/pcfree-t4'); gpu_root.mkdir(exist_ok=True)
gpu_log=gpu_root/'setup.log'
gpu_downloads=['libnvidia-gl-580','libnvidia-gpucomp-580','libnvidia-cfg1-580','xserver-xorg-video-nvidia-580']
with gpu_log.open('w') as f:
    r=subprocess.run(['apt-get','install','-y','--no-install-recommends','xserver-xorg-core'],stdout=f,stderr=subprocess.STDOUT,timeout=180)
    assert r.returncode==0, gpu_log.read_text()[-2000:]
    for pkg in gpu_downloads:
        r=subprocess.run(['apt-get','download',pkg+'=580.82.07-0ubuntu1'],cwd=gpu_root,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        assert r.returncode==0, gpu_log.read_text()[-2000:]
    for deb in gpu_root.glob('*.deb'):
        subprocess.run(['dpkg-deb','-x',str(deb),str(gpu_root/'root')],check=True)
print('T4_LIBRARIES_EXTRACTED',gpu_log.read_text()[-2500:])
print('LIBS', [str(p.relative_to(gpu_root)) for p in (gpu_root/'root').rglob('*') if p.name.startswith(('libGLX_nvidia','libEGL_nvidia','nvidia_drv','libnvidia-glcore'))])
print('DRIVER_UNCHANGED',subprocess.getoutput('nvidia-smi --query-gpu=name,driver_version --format=csv,noheader'))
