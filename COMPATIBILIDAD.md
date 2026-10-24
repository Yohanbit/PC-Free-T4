# Compatibilidad y controles

## Roblox incluido

La preparación de Flatpak y [Sober](https://sober.vinegarhq.org/) está activada por defecto, sin abrir ventanas ni retrasar la publicación del enlace. **Sober sólo se instala si la VM permite el sandbox real de Flatpak.** Al terminar correctamente aparece **Roblox - Sober** en el escritorio. Abrirlo y dejar seleccionada la instalación automática de Roblox en el primer inicio. Para omitir la preparación, desactivar `INSTALL_ROBLOX` en la celda inicial.

- Comprueba x86-64, kernel Linux >=5.11 y **SSE4.1** en todos los procesadores asignados. SSE4.2 es recomendado; no se añaden instrucciones a una CPU mediante paquetes.
- Requisitos oficiales: **OpenGL ES >=3.0**; Vulkan >=1.1 recomendado. El arranque comprueba Vulkan en la T4 y registra el perfil OpenGL ES en `opengl.log`.
- Flatpak usa su propia extensión GL/Vulkan NVIDIA, con la **misma versión exacta** que el controlador del host. No reutiliza las rutas privadas de bibliotecas del escritorio dentro del sandbox.
- Comprueba namespaces y un sandbox Bubblewrap con montaje de `/proc` **antes de descargar runtimes**. Después ejecuta `/usr/bin/true` dentro del sandbox de Sober. Prepara D-Bus de sistema si falta, necesario para la instalación de aplicaciones Flatpak. Si falla un requisito o no existe el runtime exacto, conserva el escritorio y muestra el error; no desactiva el sandbox.
- Estado: `/tmp/pcfree-selkies/sober-status.txt`. Reintento desde Colab: `_apps['roblox_background'](SESSION)`.

**Limitación comprobada en la sesión de Colab de desarrollo:** Sober se descargó, pero Bubblewrap recibió `Can't mount proc on /newroot/proc: Permission denied`. Por tanto, **Roblox no funciona en esa VM**, aunque tenga SSE4.2 y T4. El nuevo cuaderno detecta esa restricción antes de descargar los runtimes. No se garantiza Sober en todas las VMs de Colab.

Sober es comunitario y experimental, no un cliente respaldado por Roblox. Instalarlo no demuestra que un juego funcione ni garantiza compatibilidad con anticheat o mandos.

## Ratón y teclado para juegos

1. Abrir el enlace en **Chrome/Chromium actualizado**.
2. Activar **Gaming Mode** en la barra lateral, o pulsar **Ctrl+Shift+X**. Solicita pantalla completa, ratón relativo y bloqueo de teclado donde el navegador los permite. Aceptar los permisos y hacer clic dentro del escritorio para capturar el ratón.
3. **Ctrl+Shift+F** sólo cambia pantalla completa: no sustituye al modo gaming. **Ctrl+Shift+clic izquierdo** solicita captura del ratón.
4. Para liberar controles, usar la salida ofrecida por el navegador. Selkies también incluye una salida con tres pulsaciones de Esc dentro de un segundo; no asumir que una sola pulsación alcanza en todos los navegadores.

La copia privada del cliente cancela el comportamiento predeterminado de `mousedown` derecho y `contextmenu` únicamente sobre la transmisión. Los eventos siguen llegando a Selkies; no se cancelan `pointerdown` ni los clics de la barra lateral.

**Android:** algunos dispositivos asignan el botón derecho del ratón a **Atrás** antes de entregar un evento a la página. Si ocurre, buscar en los ajustes del dispositivo/ratón una asignación a **clic derecho o menú contextual**, si existe. Actualizar Chrome y usar modo gaming no garantiza que Android entregue ese evento. Si no hay ajuste disponible, reasignar apuntar a otra tecla/botón en el juego o usar otro cliente/dispositivo con captura compatible; instalar bibliotecas en Colab no corrige esa asignación local.

**Tecla Windows/Super y atajos:** Gaming Mode solicita bloqueo de Meta, Alt, Tab, Esc y menú contextual, pero el sistema operativo puede reservar algunas teclas. No se garantiza capturar Win, Alt+Tab o funciones del sistema. Evitar esas combinaciones o reasignarlas dentro del juego cuando el cliente no las entrega.

Documentación: [controles Selkies 2.0](https://github.com/selkies-project/selkies/blob/2.0.0/docs/usage.md) · [requisitos Sober](https://vinegarhq.org/Sober/Installation.html).

## Audio

El arranque escribe `~/.config/pulse/daemon.conf` (48 kHz, `s16le`, `flat-volumes=no`, `speex-float-1`, fragmentos de 40 ms), crea el sink `output` fijo a 48 kHz estéreo y lanza PulseAudio con `nice -10`. Selkies captura `output.monitor` a 96 kbps, 20 ms y RED 2, y la cola de backpressure es de 30 fragmentos (con 1 se descartaba audio al primer hipo).

Estos ajustes se aplican al iniciar: una sesión anterior al cambio debe reiniciarse. La celda de audio verifica el perfil activo y solo ajusta en caliente el volumen (100 %) y el mute. No se ha medido todavía en todos los clientes ni con todas las cargas de audio. Si el corte aparece solo en un cliente, bajar el volumen del navegador o desactivar el audio en la barra lateral para distinguir el decodificador local del servidor.

## Captura y decodificación

Selkies 2.0 decodifica con WebCodecs sobre WebSockets y elige NvFBC automáticamente cuando el driver lo permite; no existe un interruptor de servidor para forzar ninguno de los dos. La celda de captura extrae `libnvidia-fbc.so.1` de la versión exacta del driver, unifica `libxcb` con el sistema (con rollback) y verifica que los assets servidos contienen `VideoDecoder`. Las variables `PIXELFLUX_NVENC_PROFILE`, `PRESET`, `TUNING`, `RC_MODE` y `BFRAMES` no existen y no se usan; el perfil y los B-frames no se configuran desde la libreta.

NvFBC depende del driver y de que la GPU lo permita; si declina, pixelflux usa DRI3 o XShm y lo registra en el log. La decodificación por hardware se comprueba en el navegador (`chrome://gpu`, `about:support`); si el navegador no decodifica, el cliente usa la ruta de respaldo.

No se instalan controladores del kernel ni se sustituye Python del sistema. Si APT no ofrece las bibliotecas NVIDIA exactas, el arranque se detiene con un diagnóstico. No hay un tiempo de inicio fijo: depende de la VM, APT y las descargas.

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
| Roblox Player | Preparación Flatpak/Sober activada; instalación condicionada al sandbox. Bloqueado en la VM de Colab de desarrollo. |
| Paquetes Linux | Bibliotecas SDL/audio de 32 bits e instalador DEB opcionales. AppImages compatibles se extraen sin FUSE. |

Vinegar y Sober son proyectos comunitarios, no clientes Linux respaldados por Roblox. Roblox Player para Windows no se ofrece mediante Wine. No se eluden sistemas anticheat. Steam/Proton, sandbox de Electron, DRM y juegos con anticheat requieren validación individual.

Para iniciar un juego descargado con el entorno gráfico y los dispositivos virtuales:

```bash
pcfree-run /ruta/al/programa argumentos
```

