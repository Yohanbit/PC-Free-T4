# Cambios

## 2026-10-11 · diagnóstico de cierre de Steam
- Observados cierres `fatal stalled cross-thread pipe` y desconexión fatal de D-Bus en la interfaz de Steam, después de intentos de login del usuario. No hay evidencia de cierre por falta de memoria.
- Ajustado el arranque para conservar un bus privado del usuario de aplicaciones, independiente de la vida del lanzador inicial. Sin desactivar sandbox ni borrar cuentas, caché o juegos.
- En la sesión activa se comprobó respuesta del bus y procesos Steam vivos después del ajuste. Login, estabilidad prolongada y Steam Link continúan sin confirmar; no presentar este cambio como solución definitiva.
- Regenerado el cuaderno. La receta completa desde cero continúa pendiente.

## 2026-10-11 · primera receta pública
- Documentada la configuración comprobada de XFCE/T4, Firefox, RustDesk, Battly y Steam.
- Añadido cuaderno autocontenido y scripts por etapas para reconstrucción experimental.
- Añadidos controles de T4, versión de controlador y espacio; detenerse ante diferencias.
- Para nuevas sesiones, Xorg usa cookie local de autenticación en lugar de desactivar control de acceso. Ajuste de seguridad pendiente de prueba desde cero.
- Integrado arreglo acotado de Battly TAR/AppImage y dependencias Steam de 32 bits.
- Añadidos exportador/restaurador manuales de mundos y cuaderno limpio separado para Drive. Pruebas locales con archivos ficticios; no con una partida real o Drive.
- No incluidos cuentas, sesiones, IDs de conexión actuales ni datos privados.
- Steam Link, controles de Minecraft y reconstrucción completa siguen pendientes.
