# Operación

## Arranque

Usar el cuaderno autocontenido publicado en `main` (`PC-Free-T4.ipynb`). Contiene el arranque y los opcionales. Esta versión no incluye celdas de respaldo: los mundos se exportan y restauran fuera de la libreta (ver `PERSONAL-DRIVE.md`). No ejecutar el instalador sobre otro Xorg activo.

La configuración exige Ubuntu 24.04 amd64, una T4 y paquetes NVIDIA cuya versión upstream coincida exactamente con el controlador activo. Se usan los repositorios oficiales Ubuntu y NVIDIA CUDA para Ubuntu 24.04. Las bibliotecas se extraen sin instalar módulos, DKMS o controladores del kernel.

Perfil gaming: resolución automática desde 960×540/60 FPS, Turbo, H.264/NVENC con CBR 4 Mbps y cola de 120 fragmentos. Audio a 48 kHz con `flat-volumes=no`, sink fijo estéreo, PulseAudio con `nice -10` y 120 fragmentos de cola para absorber los picos de NVENC sin cortar el sonido. Chrome 156.0.8078.47-1 usa un perfil independiente en `/tmp/pcfree-selkies/chrome-profile`, EGL NVIDIA y flags de bajo consumo; es el navegador predeterminado del escritorio. Revisar `chrome://gpu` y las estadísticas de Selkies para distinguir FPS de renderizado de FPS recibidos. La GPU no acelera todo el JavaScript ni convierte un juego limitado a 15 FPS en uno de 60.

## Estado local

- `/tmp/pcfree-selkies/session.json`: usuario, entorno gráfico, rutas, controlador y procesos. No contiene contraseñas ni tokens de Colab.
- `/tmp/pcfree-selkies/access.json`: acceso temporal al escritorio; permisos `0600`.
- `/tmp/pcfree-selkies/*.log`: instalación, Xorg, Vulkan, escritorio, audio, Selkies y túnel.
- `/tmp/pcfree-selkies/chrome-status.txt`: instalación y perfil de Chrome.
- `/tmp/pcfree-selkies/sober-status.txt`: preparación de Flatpak/Sober en segundo plano; errores en `install-roblox.log`.
- `/tmp/pcfree-selkies/sober-requirements.json`: comprobaciones CPU, kernel, runtime NVIDIA y sandbox; no valida el juego.
- `/tmp/pcfree-selkies/web-client/`: copia privada del cliente oficial con protección acotada de clic derecho. No modifica los bundles originales.
- `~/.config/pcfree/game.env`: variables globales de DXVK/VKD3D que carga el lanzador de Steam; no es un perfil por juego.

Repetir el arranque conserva una sesión registrada y activa. Un estado incompleto se detiene para diagnóstico: no mata ni reconstruye servicios automáticamente.

## Aplicaciones

`pcfree-run programa [argumentos]` utiliza el usuario del escritorio y sus variables de X11, audio, D-Bus y GPU. Los dispositivos virtuales se precargan únicamente en las aplicaciones, nunca en Selkies. La expansión `$LIB` selecciona las bibliotecas de 32/64 bits por proceso.

Los instaladores no abren ventanas. Sober/Flatpak están activados por defecto en segundo plano; los demás son optativos. Cuando se seleccionan otros instaladores, esperan a Sober para no competir por APT. Steam mantiene cuentas, juegos y configuraciones; una reparación explícita pone en cuarentena únicamente los binarios redistribuibles del cliente. No ejecutar esa reparación mientras Steam esté abierto. GE-Proton11-11 se descarga desde su celda opcional, no al iniciar.

Sober necesita namespaces reales, SSE4.1 y un runtime NVIDIA exacto para Flatpak. No montar rutas de bibliotecas/ICD del host dentro del sandbox, ni precargar allí el interposer externo. El mando dentro de Flatpak requiere validación adicional. Consultar el README para Gaming Mode y límites de captura de Android/teclas reservadas.

La VM de desarrollo permitió `unshare` pero rechazó el montaje de `/proc` en Bubblewrap. La instalación de Sober terminó, su ejecución no. Por eso se comprueba también el sandbox real antes de descargar runtimes en nuevas VMs; no presentar este cambio como Roblox funcional en Colab.

Vulkan de 64 bits se verifica durante el arranque y la celda de pruebas comprueba 32/64 bits con OpenGL y Vulkan. Steam configura su propio ICD multiarch y sustituye ambas variables `VK_DRIVER_FILES` y `VK_ICD_FILENAMES` para sus procesos. No instalar bibliotecas NVIDIA de otra versión para resolver una dependencia.

## Pruebas pendientes

- Arranque integrado completo desde una VM nueva y medición de sus tiempos.
- Inicio de sesión y estabilidad de Steam; juego nativo y Proton por separado.
- Teclado relativo y mandos dentro de juegos, no únicamente en el escritorio.
- Ejecución real de Blender, Godot, Vinegar/Studio y Sober/Roblox.
- Restauración jugable de mundos y autorización individual de Drive.
- Audio medio/alto sostenido sin cortes en clientes Android y de escritorio con el perfil de 48 kHz.
- NvFBC y `VideoDecoder` confirmados en un cliente real; NvFBC puede declinar según driver o licencia.
- OpenGL/Vulkan de 32 y 64 bits y prefijos Proton 32/64 con la celda de pruebas.
- GE-Proton11-11 y un juego DX11/DX12/Vulkan/OpenGL en la T4.
- Chrome 156 con aceleración por GPU (`chrome://gpu`), navegador predeterminado y resolución automática.
- Cola de 120 y ausencia de stutter/congelación de audio, video y FPS en una sesión larga.

La sesión de desarrollo confirmó Selkies desde Android, NVENC H.264, OpenGL 4.6 y Vulkan 1.4 en la T4. Se reinstaló Steam oficial y se compilaron las bibliotecas de mandos de 32/64 bits. No extrapolar estas pruebas a login, controles o ejecución de todos los programas.

## Mantenimiento

Editar fuentes, sincronizar `scripts/` desde la libreta (`tools/build-notebooks.py`) y ejecutar las pruebas locales antes de publicar. Mantener salidas y contadores de ejecución vacíos. Nunca versionar enlaces actuales de túnel, credenciales, perfiles de aplicaciones ni partidas.

Los límites y las políticas de Colab siguen aplicándose. No añadir anti-idle, recreación automática ni cambios destinados a evitar restricciones del proveedor.
