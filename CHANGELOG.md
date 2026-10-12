# Cambios

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
