# PC-Free-T4

Escritorio Ubuntu 24.04 con GPU NVIDIA Tesla T4, XFCE y acceso HTML5 mediante Selkies 2.0. El arranque prepara OpenGL, Vulkan, audio y un enlace HTTPS autenticado. No requiere instalar un cliente remoto en el teléfono.

## Ejecutar en Google Colab

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

[Cuaderno principal](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb) · [Inicio rápido](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4-Rapido.ipynb)

1. Seleccionar **Entorno de ejecución → Cambiar tipo de entorno → GPU T4**.
2. Ejecutar el cuaderno en una VM nueva. Los instaladores opcionales están desactivados.
3. Abrir la **URL** que imprime Colab e introducir el **usuario y la contraseña** generados para esa sesión.
4. Usar Chrome/Chromium actualizado. Pantalla completa, teclado, ratón relativo y mandos dependen del navegador y del dispositivo.

El cuaderno contiene sus fuentes: no necesita clonar GitHub


## Configuración

| Componente | Implementación |
| --- | --- |
| Escritorio | XFCE sin compositor; Xorg local autenticado, 1280 × 720 |
| Renderizado | Bibliotecas NVIDIA de la misma versión que el controlador del host; extracción aislada |
| APIs 3D | OpenGL y Vulkan de 64 bits; multiarch opcional para Steam/Wine |
| Transmisión | Selkies 2.0, WebSockets, H.264/NVENC cuando está disponible |
| Transporte externo | Cloudflare Tunnel por HTTP/2; origen limitado a loopback |
| Audio | PulseAudio, salida virtual y monitor de captura |
| Aplicaciones | Usuario sin privilegios y D-Bus persistente |
| Ajustes iniciales | 720p, 30 FPS, 2 Mbps; modificables desde el cliente |

Firefox se descarga en segundo plano y crea su acceso directo cuando termina. Archivos, Descargas, Terminal e instalador limitado de paquetes Ubuntu quedan preparados. Las esperas usan comprobaciones de disponibilidad.

 No hay un tiempo de inicio fijo: depende de la VM, APT y las descargas.

## Aplicaciones y juegos opcionales

Activar únicamente las casillas necesarias y ejecutar esa celda. La instalación no abre aplicaciones automáticamente.

| Opción | Fuente / alcance |
| --- | --- |
| Steam | [Cliente oficial](https://store.steampowered.com/about/), bibliotecas NVIDIA de 32/64 bits y lanzador no-root. El acceso a la cuenta sigue pendiente de validación. |
| Mandos | [Input Interposer y fake-udev](https://docs.selkies.io/latest/components/input-interposer), sin depender de `/dev/uinput`. Necesita aplicaciones iniciadas con `pcfree-run`. |
| Wine y Winetricks | Paquetes Ubuntu para programas Windows. No equivalen a compatibilidad universal. |
| Lutris / Heroic | [Lutris](https://lutris.net/) desde Ubuntu; [Heroic](https://heroicgameslauncher.com/) desde su publicación oficial. |
| Minecraft | [Prism Launcher](https://prismlauncher.org/) y Java 21. Requiere cuenta y versión/mods compatibles. |
| Blender | Paquete nativo de Ubuntu. [Proyecto oficial](https://www.blender.org/). |
| Godot | Editor Linux x86_64 de la [publicación oficial](https://godotengine.org/download/linux/). |
| Roblox Studio | [Vinegar](https://vinegarhq.org/Vinegar/Installation.html) compilado desde su código oficial. Experimental; Wine y Studio se descargan al abrirlo. |
| Roblox Player | [Sober](https://sober.vinegarhq.org/) mediante Flatpak oficial. Comprueba primero el sandbox del kernel; si no está disponible, cancela la instalación. Juego no validado. |
| Paquetes Linux | Bibliotecas SDL/audio de 32 bits e instalador DEB opcionales. AppImages compatibles se extraen sin FUSE. |

 con anticheat requieren validación individual.

Para iniciar un juego descargado con el entorno gráfico y los dispositivos virtuales:

```bash
pcfree-run /ruta/al/programa argumentos
```

## Seguridad y persistencia

- URL y contraseña temporales, generadas por sesión. El túnel publica un acceso autenticado en Internet; no compartir las credenciales.
- No guardar salidas del cuaderno en GitHub. El disco de la VM y las sesiones de las aplicaciones son temporales.
- Exportar mundos manualmente desde el cuaderno. Restaurar crea carpetas nuevas, sin sobrescribir mundos existentes.
- [Respaldos separados en Google Drive](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb). Drive no se monta durante el arranque del escritorio.

## Desarrollo y diagnóstico

`scripts/selkies-desktop.py` contiene el arranque; `compat-steam.py` y `compat-apps.py`, los opcionales. Estado y registros: `/tmp/pcfree-selkies/`. Consultar [operación](CONTINUAR.md) y [cambios](CHANGELOG.md).

```bash
python3 tools/build-notebooks.py
python3 tests/test_package.py
python3 tests/test_quick_start.py
python3 tests/test_selkies.py
python3 tests/test_steam_setup.py
python3 tests/test_apps.py
```
