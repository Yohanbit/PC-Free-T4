# Cambios

## 2026-10-25 · componentes actualizados y compatibilidad Proton

- Selkies 2.1.0 con pixelflux 2.2.1 y pcmflux 2.2.0 incluidos; cloudflared 2026.10.3; Chrome 156.0.8078.47-1; GE-Proton11-11 y Proton 11.0-2. Los SHA-256/SHA-512 oficiales se verifican antes de usar cada descarga.
- Chrome queda como navegador predeterminado, con perfil aislado, EGL/NVIDIA, límite de procesos y sin servicios de fondo. Se retira Firefox.
- Resolución automática de Selkies (`--enable-resize=true`, máximo Xorg 1920×1080) y cola de 120 fragmentos para absorber hipos sin descartar audio ni video.
- Se eliminan la celda de audio independiente, la celda de Xorg sin efecto y la prioridad duplicada; las prioridades quedan en una sola celda moderada.
- Se borran los instaladores `.deb`/archivos temporales al terminar y se limpia APT para liberar espacio; Chrome limita procesos y caché en disco.
- Se retira la descarga del wheel de pixelflux 59c523a: 2.2.1 ya incorpora la declinación de NvFBC cuando `libX11` usa otra copia de `libxcb` (notas de pixelflux 2.2.0). El resto de parches P1, P2, P4-P22 se conserva.
- Perfil explícito para Selkies 2.1: CBR, 4 Mbps, 60 FPS, 960×540, cola 30, congestión desactivada, `frame-ancestors=self`, paint-over desactivado, segunda pantalla desactivada y audio 96 kbps/20 ms/RED 2. Así los nuevos defaults no cambian el perfil sin medirlo.
- Librerías de compatibilidad 32/64 bits, códecs GStreamer/VA-API/VDPAU, OpenAL/SDL2 y herramientas de compilación multilib.
- Celda 11 reescrita: `DXVK_SHADER_CACHE_PATH` y `VKD3D_SHADER_CACHE_PATH` reales, sin `DXVK_ASYNC`, `VKD3D_SHADER_CACHE`, `PROTON_NO_ESYNC`, `PROTON_NO_FSYNC=0`, `WINEPREFIX` ni `MESA_VK_WSI_PRESENT_MODE`. El lanzador de Steam carga `~/.config/pcfree/game.env`.
- GE-Proton11-11 se descarga bajo demanda (no al iniciar), con SHA-512 y extracción validada.
- Nueva celda de pruebas Proton: OpenGL/Vulkan 32/64 bits y arranque de prefijos Proton de 64 y 32 bits.
- DXVK y VKD3D-Proton se actualizan con el runtime elegido (GE-Proton11-11 o Proton 11); no se instalan sueltos para no romper el runtime del juego.

## 2026-10-24 · preparación aplicada y limpieza conservadora
- La celda de preparación publica el núcleo parcheado en `SOURCES` y lo recompila. Antes los parches se descartaban y el arranque usaba el código sin cambios, pese a imprimir `[OK]`.
- Reejecutar la preparación ya no duplica parches: cada sustitución comprueba primero si ya está aplicada.
- La limpieza ya no borra `cloudflared` con el túnel activo, conserva las listas de APT y la documentación, y deja `autoremove` desactivado por defecto.
- Documentación alineada: sin referencias a cuadernos retirados; se aclara que esta versión no incluye celdas de respaldo de mundos.
- Añadidas pruebas offline que ejecutan la celda de preparación y verifican publicación, idempotencia y compilación, además del orden seguro de la limpieza.
- Audio estable: `daemon.conf` se escribe al iniciar (48 kHz, `s16le`, `flat-volumes=no`, `speex-float-1`, fragmentos de 40 ms), el sink `output` se crea fijo a 48 kHz y PulseAudio arranca con `nice -10`.
- La cola de backpressure pasa de 1 a 30 fragmentos: con 1 se descartaba cualquier fragmento (audio incluido) al primer hipo, la causa más probable de los cortes con volumen medio/alto.
- Selkies limita el audio a 96 kbps estéreo, 20 ms y RED 2; la celda de audio verifica el perfil activo en lugar de fingir aplicarlo.
- Celda de captura reescrita: extrae `libnvidia-fbc.so.1` de la versión exacta del driver, unifica `libxcb` con rollback y verifica WebCodecs en los assets servidos. Se retiran `window.SELKIES_CONFIG`, `PIXELFLUX_NVENC_*` y los emojis; solo se aplican flags que existen en Selkies.

## 2026-10-12 · perfil gaming NVIDIA
- Perfil predeterminado 720p/60 FPS objetivo, H.264 NVENC cuando está disponible, Turbo y CBR 5 Mbps. Selección GPU NVIDIA y preferencia de codificación CPU desactivada.
- Firefox con perfil dedicado, WebRender/WebGL y EGL NVIDIA aislado. No modifica cuentas de otros perfiles ni desactiva sandbox.
- Botón Jugar en cada nueva sesión: solicita captura con una acción del usuario; no fuerza permisos del navegador.
- El objetivo de transmisión no equivale a FPS del juego. Rendimiento de aplicaciones y captura desde Android pendiente de medición.

## 2026-10-12 · Sober incluido y controles web
- Flatpak/Sober activados por defecto, descarga en segundo plano después de publicar el escritorio; opción para omitirla.
- Comprobaciones x86-64, SSE4.1/SSE4.2, kernel y namespaces, extensión NVIDIA exacta de Flatpak y prueba no gráfica del sandbox.
- Estado y errores de instalación separados; reintento sin reiniciar el escritorio y exclusión de instalaciones simultáneas de Sober.
- Copia privada del cliente Selkies con cancelación acotada del comportamiento predeterminado de clic derecho, sin impedir su envío al escritorio.
- Modo gaming y límites de Android/Keyboard Lock documentados. No se promete interceptar Atrás ni atajos consumidos por el sistema local.
- Registro de OpenGL ES y Vulkan NVIDIA en el arranque. Pruebas offline ampliadas; Roblox y controles reales pendientes de validación.
- Prueba real: CPU SSE4.1/SSE4.2 disponible; Sober y extensión NVIDIA descargados, pero ejecución bloqueada por montaje de `/proc` denegado en Bubblewrap. Nuevo preflight evita descargar runtimes en VMs con esa restricción.

## 2026-10-12 · escritorio HTML5 y arranque mínimo
- Sustituido el flujo de acceso anterior por Selkies 2.0 y túnel HTTPS HTTP/2 autenticado.
- Cuadernos autocontenidos con fuentes embebidas, credenciales nuevas por sesión y salidas limpias.
- Escritorio 720p sin compositor; usuario no-root, D-Bus persistente y audio virtual autenticado.
- OpenGL y Vulkan con bibliotecas NVIDIA exactas y aisladas; validación del renderizador antes de publicar el acceso.
- Firefox en segundo plano, accesos preparados y ninguna aplicación abierta por el instalador.
- Steam oficial opcional con soporte multiarch y cuarentena limitada de binarios. Inicio de sesión aún no validado.
- Mandos opcionales mediante Input Interposer/fake-udev para ambos ELF.
- Añadidos opcionales Wine, Lutris, Heroic, Prism/Java, Blender, Godot, Vinegar/Studio y Sober con comprobación del sandbox.
- Retirados los scripts de acceso remoto antiguos del flujo distribuido. Respaldos manuales separados conservados.
- Pruebas locales de configuración y privacidad. Arranque integrado desde una VM nueva y aplicaciones/juegos pendientes de validación.

## 2026-10-11 · instrucciones para retomar y acceso provisional
- Guardadas las peticiones «Ejecuta mi repositorio PC-Free-T4» y «Arranca PC-Free-T4 y continúa donde lo dejamos», con lectura de main y comprobación de sesión existente antes de reconstruir.
- Aclarado que RustDesk es temporal para administrar el escritorio; Steam Link sigue en pruebas, sin login, emparejamiento ni controles confirmados.
- Conservado el próximo paso: validar login de Steam y luego controles/cámara desde Android, manteniendo RustDesk como respaldo y sin cerrar la partida.
- Diferenciada la configuración publicada de los datos de la sesión: todavía no hay respaldo real verificado de la partida. Cambio documental, sin modificar el runtime ni los scripts.

## 2026-10-11 · diagnóstico de cierre de Steam
- Observados cierres `fatal stalled cross-thread pipe` y desconexión fatal de D-Bus en la interfaz de Steam, después de intentos de login del usuario. No hay evidencia de cierre por falta de memoria.
- Ajustado el arranque para conservar un bus privado del usuario de aplicaciones, independiente de la vida del lanzador inicial. Sin desactivar sandbox ni borrar cuentas, caché o juegos.
- En la sesión activa se comprobó respuesta del bus y procesos Steam vivos después del ajuste. Login, estabilidad prolongada y Steam Link continúan sin confirmar; no presentar este cambio como solución definitiva.
- Regenerado el cuaderno. La receta completa desde cero continúa pendiente.
- Steam bloqueado requirió terminar únicamente sus procesos y abrir con `-cef-disable-gpu`: apareció de nuevo la pantalla de login. El parámetro afecta a la interfaz web de Steam, no a la GPU de Minecraft. Añadido al arranque; falta probar que completa el login y no vuelve a cerrarse.

## 2026-10-11 · primera receta pública
- Documentada la configuración comprobada de XFCE/T4, Firefox, RustDesk, Battly y Steam.
- Añadido cuaderno autocontenido y scripts por etapas para reconstrucción experimental.
- Añadidos controles de T4, versión de controlador y espacio; detenerse ante diferencias.
- Para nuevas sesiones, Xorg usa cookie local de autenticación en lugar de desactivar control de acceso. Ajuste de seguridad pendiente de prueba desde cero.
- Integrado arreglo acotado de Battly TAR/AppImage y dependencias Steam de 32 bits.
- Añadidos exportador/restaurador manuales de mundos y cuaderno limpio separado para Drive. Pruebas locales con archivos ficticios; no con una partida real o Drive.
- No incluidos cuentas, sesiones, IDs de conexión actuales ni datos privados.
- Steam Link, controles de Minecraft y reconstrucción completa siguen pendientes.
