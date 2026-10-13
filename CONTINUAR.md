# Operación

## Arranque

Usar los cuadernos autocontenidos publicados en `main`. El cuaderno principal incluye respaldo manual; el inicio rápido contiene el mismo arranque y los mismos opcionales. No ejecutar el instalador sobre otro Xorg activo.

La configuración exige Ubuntu 24.04 amd64, una T4 y paquetes NVIDIA cuya versión upstream coincida exactamente con el controlador activo. Se usan los repositorios oficiales Ubuntu y NVIDIA CUDA para Ubuntu 24.04. Las bibliotecas se extraen sin instalar módulos, DKMS o controladores del kernel.

Perfil gaming: 720p/60 FPS objetivo, Turbo, H.264/NVENC cuando está disponible y CBR 5 Mbps. Firefox usa un perfil independiente en `/tmp/pcfree-selkies/firefox-profile`, EGL NVIDIA y preferencias WebRender/WebGL. No se desactiva su sandbox. Revisar `about:support` → Gráficos en Firefox y estadísticas de Selkies para distinguir FPS de renderizado de FPS recibidos. La GPU no acelera todo el JavaScript ni convierte un juego limitado a 15 FPS en uno de 60.

## Abrir la versión vigente en Colab

Abre el cuaderno directamente desde la rama main del repositorio:

- [Cuaderno principal](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)
- [Inicio rápido](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4-Rapido.ipynb)

Un cuaderno que ya estaba abierto o que se guardó en Drive es una copia y no se actualiza cuando cambia GitHub. Cierra esa pestaña y abre uno de los enlaces anteriores; comprueba que la dirección contiene /github/Yohanbit/PC-Free-T4/blob/main/. Para probar cambios desde cero, guarda primero cualquier archivo que necesites y luego desconecta/elimina el entorno de ejecución anterior antes de ejecutar todo en una VM nueva. Esto borra el disco temporal y la salida de esa VM. Usa escritorio remoto únicamente en un entorno donde el proveedor lo permita; Google restringe los escritorios remotos en Colab administrado gratuito cuando no hay saldo positivo de unidades de cómputo ([política de Colab](https://research.google.com/colaboratory/faq.html#disallowed-activities)).

## Validación manual del primer inicio de Steam (pendiente)

Steam ya tiene una celda opcional en ambos cuadernos: INSTALL_STEAM = False y STEAM_GAMEPADS = False. En un entorno permitido y compatible, inicia el escritorio, conecta la sesión, cambia solo INSTALL_STEAM a True y ejecuta esa celda. La celda instala el cliente oficial, pero no lo abre; inicia Steam manualmente desde el menú de aplicaciones. Mantén mandos desactivados durante la primera prueba.

Registra si aparece la ventana de login, si se mantiene abierta, qué ocurre al intentar iniciar sesión y cuánto tarda en cerrarse o fallar. Para diagnosticar, conserva el registro de instalación ~/.local/share/pcfree/steam/install.log y, si existen, los registros de Steam bajo ~/.local/share/Steam/logs/. Comparte solo fragmentos saneados: elimina nombres de usuario, correo, códigos, cookies, tokens y cualquier dato de la cuenta. No compartas la salida del cuaderno si contiene credenciales de acceso al escritorio.

El instalador informa login_validated: false: instalar Steam no demuestra que el login funcione. No activar inicio automático, no desactivar el sandbox ni añadir opciones de CEF como prueba a ciegas; cualquier cambio de compatibilidad debe basarse en el resultado y los registros de una ejecución permitida.

## Estado local

- `/tmp/pcfree-selkies/session.json`: usuario, entorno gráfico, rutas, controlador y procesos. No contiene contraseñas ni tokens de Colab.
- `/tmp/pcfree-selkies/access.json`: acceso temporal al escritorio; permisos `0600`.
- `/tmp/pcfree-selkies/*.log`: instalación, Xorg, Vulkan, escritorio, audio, Selkies y túnel.
- `/tmp/pcfree-selkies/firefox-status.txt`: descarga en segundo plano, completada o fallida.
- `/tmp/pcfree-selkies/sober-status.txt`: preparación de Flatpak/Sober en segundo plano; errores en `install-roblox.log`.
- `/tmp/pcfree-selkies/sober-requirements.json`: comprobaciones CPU, kernel, runtime NVIDIA y sandbox; no valida el juego.
- `/tmp/pcfree-selkies/web-client/`: copia privada del cliente oficial con protección acotada de clic derecho. No modifica los bundles originales.

Repetir el arranque conserva una sesión registrada y activa. Un estado incompleto se detiene para diagnóstico: no mata ni reconstruye servicios automáticamente.

## Aplicaciones

`pcfree-run programa [argumentos]` utiliza el usuario del escritorio y sus variables de X11, audio, D-Bus y GPU. Los dispositivos virtuales se precargan únicamente en las aplicaciones, nunca en Selkies. La expansión `$LIB` selecciona las bibliotecas de 32/64 bits por proceso.

Los instaladores no abren ventanas. Sober/Flatpak están activados por defecto en segundo plano; los demás son optativos. Cuando se seleccionan otros instaladores, esperan a Sober para no competir por APT. Steam mantiene cuentas, juegos y configuraciones; una reparación explícita pone en cuarentena únicamente los binarios redistribuibles del cliente. No ejecutar esa reparación mientras Steam esté abierto.

Sober necesita namespaces reales, SSE4.1 y un runtime NVIDIA exacto para Flatpak. No montar rutas de bibliotecas/ICD del host dentro del sandbox, ni precargar allí el interposer externo. El mando dentro de Flatpak requiere validación adicional. Consultar el README para Gaming Mode y límites de captura de Android/teclas reservadas.

La VM de desarrollo permitió `unshare` pero rechazó el montaje de `/proc` en Bubblewrap. La instalación de Sober terminó, su ejecución no. Por eso se comprueba también el sandbox real antes de descargar runtimes en nuevas VMs; no presentar este cambio como Roblox funcional en Colab.

Vulkan de 64 bits se verifica durante el arranque. Steam configura su propio ICD multiarch y sustituye ambas variables `VK_DRIVER_FILES` y `VK_ICD_FILENAMES` para sus procesos. No instalar bibliotecas NVIDIA de otra versión para resolver una dependencia.

## Pruebas pendientes

- Arranque integrado completo desde una VM nueva y medición de sus tiempos.
- Inicio de sesión y estabilidad de Steam; juego nativo y Proton por separado.
- Teclado relativo y mandos dentro de juegos, no únicamente en el escritorio.
- Ejecución real de Blender, Godot, Vinegar/Studio y Sober/Roblox.
- Restauración jugable de mundos y autorización individual de Drive.

La sesión de desarrollo confirmó Selkies desde Android, NVENC H.264, OpenGL 4.6 y Vulkan 1.4 en la T4. Se reinstaló Steam oficial y se compilaron las bibliotecas de mandos de 32/64 bits. No extrapolar estas pruebas a login, controles o ejecución de todos los programas.

## Mantenimiento

Editar fuentes, regenerar los cuadernos y ejecutar las pruebas locales antes de publicar. Mantener salidas y contadores de ejecución vacíos. Nunca versionar enlaces actuales de túnel, credenciales, perfiles de aplicaciones ni partidas.

Los límites y las políticas de Colab siguen aplicándose. No añadir anti-idle, recreación automática ni cambios destinados a evitar restricciones del proveedor.
