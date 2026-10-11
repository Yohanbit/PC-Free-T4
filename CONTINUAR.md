# Punto de continuación · 11 octubre 2026

## Propósito
Reconstruir una sesión Linux con GPU y acceso desde Android, conservando cambios de configuración en este repositorio. PC-Free Windows en Codespaces es un proyecto separado y no se borra ni se reinicia por ejecutar esta receta.

## Comprobado en la sesión original
- NVIDIA Tesla T4, controlador 580.82.07 y OpenGL 4.6 mediante bibliotecas oficiales aisladas.
- Xorg :98 y XFCE 1280×720; demo gráfica NVIDIA ejecutada antes de abrir juegos.
- RustDesk 1.4.4 mostró Ready y el usuario confirmó conexión real desde Android.
- Teclado y ratón funcionan en aplicaciones del escritorio remoto.
- Firefox oficial instalado como usuario de aplicaciones, sin desactivar sandbox.
- Battly Linux TAR 3.0.1 descargado oficialmente, con SHA256 verificado y arreglo acotado del actualizador que quedaba esperando AppImage.
- Usuario abrió un mundo de Minecraft. La captura más reciente dice 26.3; no afirmar que se comprobó 1.21.11.
- Steam oficial actualizado, dependencias de 32 bits corregidas y pantalla de inicio de sesión observada. No está confirmado el login ni Steam Link.

## Pendiente
- Tras terminar solo los procesos bloqueados de Steam y abrir con `-cef-disable-gpu`, volvió a aparecer la pantalla de login. El acceso directo conserva ese parámetro para la interfaz; Minecraft sigue abierto y no se cambió su aceleración gráfica. Pedir prueba real de login desde RustDesk; aún no confirmar solución definitiva.
- Steam se cerró tras intentos de login: registros muestran bloqueo interno y desconexión fatal de D-Bus. Se probó bus privado persistente y se observaron procesos vivos/respuesta del bus; el inicio de sesión y la estabilidad siguen pendientes. No usar contraseñas del chat, borrar perfiles ni cerrar Minecraft para probar.
- RustDesk transmite mal el caminar sostenido y no permite girar la cámara en la partida. Causa exacta no establecida; no culpar a GPU ni a Minecraft sin medir.
- Probar Steam Link con cuenta del usuario, sin compras, y comprobar controles/cámara. Falta /dev/uinput en el entorno original: no asumir soporte completo de entrada.
- Medir rendimiento, sonido y estabilidad. No derivar FPS de Minecraft de una demo OpenGL.
- Reconstrucción integrada desde cero y flujo real de exportación/restauración de mundos/Drive pendientes de validación. No cerrar la sesión actual solo para probar el instalador.

## Precauciones y persistencia
- GPU gratuita y duración no garantizadas; Colab restringe el escritorio remoto. No usar anti-idle, evasión, túneles destinados a eludir límites ni recreación automática.
- El repositorio guarda código, no memoria de la máquina, contraseñas, partidas ni sesiones de cuentas.
- No montar Drive en el runtime de escritorio. Para Drive, usar respaldo descargado y app de Drive, o el cuaderno CPU limpio separado.
- Mantener datos de conexión solo en interfaz/salida privada. No guardar ID o contraseña temporal, QR de login ni tokens en archivos o commits.
- No sobreescribir partidas; restaurar en nuevas carpetas y comprobar compatibilidad de versión/mods.

## Retomar
Leer archivos vigentes del repo antes de cambiar nada. Si la máquina sigue viva, conectar a ella: no lanzar una nueva innecesariamente. Si ya desapareció, usar el cuaderno y recuperar los mundos desde el último respaldo disponible. El usuario deberá completar login/CAPTCHA/emparejamiento cuando el servicio lo pida.

## Mantener el repositorio
Actualizar scripts, regenerar cuadernos, ejecutar pruebas, revisar privacidad, actualizar CHANGELOG/estado y publicar un commit mínimo en main. No afirmar que una modificación publicada está aplicada al runtime activo hasta ejecutarla y observar su resultado.
