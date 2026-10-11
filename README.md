PC-Free-T4

Entorno Linux experimental con aceleración gráfica NVIDIA en Google Colab

PC-Free-T4 es un proyecto experimental para reconstruir un entorno de escritorio Linux con aceleración gráfica NVIDIA a partir de scripts de instalación, configuración reproducible y notebooks de Google Colab.

El entorno de referencia integra Ubuntu 24.04, XFCE, NVIDIA Tesla T4, Firefox, Battly, RustDesk y Steam. El proyecto permite automatizar parte de la preparación del entorno y gestionar la exportación y restauración de mundos de Minecraft mediante archivos de respaldo.

PC-Free-T4 no es una imagen de disco, una máquina virtual persistente ni una copia de Windows. Los notebooks y scripts describen el procedimiento de preparación; los archivos de la sesión activa requieren una estrategia de persistencia independiente.

Accesos directos

""Abrir escritorio en Google Colab" (https://colab.research.google.com/assets/colab-badge.svg)" (https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

"Notebook de respaldos para Google Drive" (https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb)

"Condiciones de uso de Google Colab" (https://research.google.com/colaboratory/faq.html#disallowed-activities)

---

1. Arquitectura del repositorio

El repositorio separa los procedimientos de instalación de los cuadernos ejecutables y de las herramientas de validación.

Componente| Función
"scripts/"| Scripts reutilizables de instalación, configuración y preparación del entorno.
"PC-Free-T4.ipynb"| Notebook principal de Google Colab. Orquesta las etapas de preparación del escritorio.
"Drive-Backups.ipynb"| Notebook independiente para transferir respaldos a Google Drive desde un entorno CPU.
"tools/build-notebooks.py"| Genera o actualiza los notebooks a partir de los archivos fuente utilizados por el proyecto.
"tests/test_package.py"| Ejecuta las comprobaciones automatizadas definidas para el paquete.
"CHANGELOG.md"| Historial técnico de modificaciones y mejoras.
"CONTINUAR.md"| Contexto operativo para retomar el trabajo entre sesiones.

Fuente de verdad: el código fuente y la documentación versionados en GitHub. Los notebooks deben generarse y validarse después de modificar los archivos fuente correspondientes.

La presencia de un componente en el repositorio no implica que todas sus funciones estén validadas en una sesión real. Consultar el código y las pruebas antes de considerar una capacidad como estable.

2. Plataforma de referencia

La configuración utilizada durante las pruebas se basa en los siguientes parámetros:

Parámetro| Referencia
Sistema operativo| Ubuntu 24.04
Entorno de escritorio| XFCE
GPU| NVIDIA Tesla T4
Controlador NVIDIA observado| "580.82.07"
Acceso remoto| RustDesk
Navegador| Firefox
Plataforma de juegos| Steam
Launcher adicional| Battly
Entorno de ejecución| Sesión de Google Colab, sujeta a disponibilidad

Estos valores describen el entorno de referencia y no constituyen una garantía de que Google Colab proporcione la misma configuración en cada ejecución.

Dependencias gráficas

Las bibliotecas gráficas se preparan de forma aislada para reducir el riesgo de interferir con el controlador NVIDIA del sistema. La receta comprueba la compatibilidad de las versiones necesarias y debe detenerse cuando no pueda verificar las condiciones esperadas.

No se debe forzar una versión de controlador o sustituir componentes del kernel únicamente para superar un error de instalación. Ante una discrepancia, hay que revisar la versión disponible, las dependencias y los mensajes de diagnóstico antes de continuar.

3. Requisitos y restricciones de ejecución

- Almacenamiento: disponer de al menos 8 GiB libres como referencia inicial. Juegos, bibliotecas y respaldos requieren capacidad adicional.
- Aceleración gráfica: la disponibilidad de una Tesla T4 depende de los recursos que Google Colab asigne a la sesión. No está garantizada.
- Cuota y duración: los límites de ejecución, la disponibilidad de GPU y la duración de las sesiones pueden variar.
- Persistencia: el entorno de ejecución no debe tratarse como almacenamiento permanente.
- Conectividad: el acceso remoto requiere que la sesión permanezca activa y que el servicio de conexión esté disponible.
- Pagos: el procedimiento documentado no activa por sí mismo un plan de pago. El usuario debe revisar las opciones y condiciones de su cuenta.

Antes de ejecutar el proyecto, deben revisarse las "condiciones oficiales de Google Colab" (https://research.google.com/colaboratory/faq.html#disallowed-activities). La implementación debe mantenerse dentro de los usos permitidos por el proveedor. No se deben utilizar mecanismos para eludir cuotas, restricciones de acceso o controles de la plataforma.

4. Procedimiento de despliegue

4.1 Preparación

1. Leer este documento y las condiciones de uso del proveedor.
2. Abrir "PC-Free-T4.ipynb" desde el enlace de Google Colab.
3. Seleccionar, cuando esté disponible y permitido, un entorno con GPU NVIDIA T4. No habilitar pagos como parte automática del procedimiento.
4. Iniciar la ejecución en un entorno nuevo, sin asumir que una instalación anterior permanece disponible.
5. Ejecutar las etapas numeradas del notebook en el orden establecido.
6. Si una comprobación de compatibilidad falla, detener el proceso e inspeccionar la salida correspondiente. No omitir validaciones para forzar una instalación aparentemente completada.

El notebook principal contiene el código necesario para ejecutar sus etapas sin depender de que el repositorio esté accesible durante cada fase de la ejecución. La disponibilidad de dependencias externas sigue estando sujeta a sus respectivas fuentes y condiciones de acceso.

4.2 Validación de la aceleración gráfica

Una instalación completada no demuestra por sí sola que la GPU se esté utilizando en las aplicaciones gráficas.

Cuando las herramientas correspondientes estén disponibles, ejecutar:

glxinfo -B

Comprobar que el renderizador identificado sea NVIDIA Tesla T4 y no "llvmpipe". Revisar también la información del controlador y cualquier advertencia de inicialización gráfica.

Si el renderizador indica "llvmpipe", no debe considerarse validada la aceleración por hardware. Hay que investigar la configuración gráfica, las bibliotecas cargadas y la compatibilidad del entorno.

4.3 Acceso remoto con RustDesk

Una vez iniciado el escritorio:

1. Abrir RustDesk y obtener el identificador y la contraseña temporal generados por la sesión.
2. Mantener esas credenciales privadas y compartirlas únicamente con el dispositivo autorizado.
3. Instalar el cliente de Android desde la distribución oficial de RustDesk.
4. Establecer la conexión y comprobar que el escritorio responde a la entrada táctil y al teclado.

El identificador y la contraseña son datos de conexión de la sesión, no credenciales permanentes del proyecto. Deben generarse y verificarse nuevamente cuando corresponda.

4.4 Aplicaciones

Firefox, Battly y Steam disponen de accesos directos cuando la preparación correspondiente se completa correctamente. El inicio de sesión, la selección de juegos y las versiones utilizadas requieren intervención del usuario.

Steam puede necesitar varios minutos para completar la actualización inicial. El tiempo real depende del estado de la sesión, la conexión y los archivos que deban descargarse.

Consideración sobre Battly

La corrección aplicada a Battly "3.0.1" evita el actualizador AppImage que presentaba problemas con el paquete TAR de Linux utilizado por el proyecto y conserva una copia del archivo original.

Esta modificación no implica una actualización automática del launcher. Battly debe actualizarse manualmente desde una fuente oficial. La corrección descrita no pretende modificar el sistema de autenticación de Battly ni el del juego.

5. Persistencia y ciclo de vida de las sesiones

GitHub almacena el código fuente, los notebooks versionados y el historial de cambios. No conserva automáticamente el estado de una máquina de Google Colab.

Cuando una sesión termina o deja de estar disponible, puede ser necesario reinstalar los componentes, regenerar los datos de conexión e iniciar sesión de nuevo.

Elemento| Persistencia
Scripts y documentación versionados| GitHub
Notebook guardado como documento| Repositorio y/o ubicación donde se haya guardado
Entorno de escritorio en ejecución| No garantizado
Archivos personales y configuraciones locales| No garantizados
Mundos exportados a un ZIP| Solo mientras el archivo de respaldo se conserve
Copia subida a Google Drive| Depende de que la transferencia termine correctamente y el archivo permanezca disponible

Guardar el notebook en Google Drive no equivale a respaldar el contenido del escritorio. Del mismo modo, conservar el repositorio no permite reconstruir automáticamente los archivos personales de una sesión anterior.

6. Exportación de mundos de Minecraft

La función de exportación está destinada a preservar mundos seleccionados. No equivale a una copia integral de Minecraft ni del entorno de escritorio.

6.1 Preparación del mundo

Antes de exportar:

1. Abrir Minecraft y utilizar Guardar y salir para cerrar correctamente el mundo.
2. Ejecutar la celda de exportación del notebook.
3. Revisar la lista de mundos detectados y seleccionar explícitamente los índices correspondientes.
4. Confirmar que el proceso haya generado el ZIP esperado y el manifiesto de integridad.
5. Conservar el archivo resultante fuera del entorno de ejecución, por ejemplo, descargándolo al dispositivo.

No se recomienda exportar un mundo mientras permanece abierto. Los archivos pueden cambiar durante la lectura y generar un respaldo inconsistente.

6.2 Contenido del respaldo

El formato documentado incluye los mundos seleccionados y un manifiesto de integridad. No constituye una copia completa de los siguientes elementos:

- Instalación de Minecraft o del launcher.
- Perfiles y datos de autenticación.
- Perfiles de Firefox.
- Datos de Steam o RustDesk.
- Ajustes generales del escritorio.
- Mods, bibliotecas y dependencias de la instancia.

Para conservar un mundo modificado, también hay que registrar las versiones de Minecraft, el loader y los mods necesarios para abrirlo de forma compatible.

6.3 Transferencia a Google Drive

Hay dos flujos previstos:

Transferencia manual

1. Descargar el ZIP de respaldo al dispositivo.
2. Subir el archivo a Google Drive mediante la aplicación o la interfaz web.

Transferencia con el notebook de respaldos

1. Abrir "Drive-Backups.ipynb" en un entorno CPU limpio e independiente.
2. Subir el archivo ZIP al entorno.
3. Autorizar explícitamente el acceso a Google Drive cuando se solicite.
4. Ejecutar el flujo para copiar el respaldo a "MyDrive/PC-Free-Backups/".
5. Confirmar que el archivo se haya transferido correctamente y desmontar Drive al terminar.

El notebook de respaldos debe mantenerse separado del escritorio principal. No se deben ejecutar aplicaciones innecesarias ni utilizar ese entorno para otras tareas mientras Drive esté montado.

6.4 Restauración

Para restaurar un mundo:

1. Obtener el ZIP desde la ubicación donde se guardó el respaldo.
2. Abrir la instancia de Minecraft de destino.
3. Identificar la carpeta "saves" correspondiente a esa instancia.
4. Indicar la ruta correcta en la celda de restauración.
5. Ejecutar la validación y confirmar el resultado antes de abrir Minecraft.

La restauración comprueba las rutas y la integridad previstas por la implementación y crea carpetas nuevas para evitar sobrescribir mundos existentes. No debe ejecutarse contenido desconocido procedente de respaldos ajenos.

Estado de validación: la exportación, restauración y transferencia mediante Drive se han probado con archivos ficticios. Todavía no se han validado integralmente con una partida real ni con la cuenta de Google Drive del usuario. Por tanto, estas funciones no deben considerarse verificadas de extremo a extremo.

7. Administración remota y pruebas de streaming

RustDesk se conserva como mecanismo principal de administración remota y como conexión de respaldo durante las pruebas.

No se considera una solución validada para transmitir Minecraft con una experiencia de juego satisfactoria. La evaluación de Steam Link continúa pendiente de completar.

Secuencia de validación de Steam Link

1. Comprobar que Steam inicia sesión correctamente en el entorno remoto.
2. Verificar la disponibilidad de las funciones de transmisión.
3. Emparejar el dispositivo Android siguiendo el procedimiento oficial.
4. Probar el movimiento sostenido, el giro de cámara, la entrada táctil, el teclado y los controles necesarios.
5. Comprobar el audio, la latencia percibida y la estabilidad durante una sesión prolongada.
6. Conservar RustDesk hasta que la alternativa haya superado las pruebas funcionales.

No cerrar la sesión ni retirar el mecanismo de acceso remoto de respaldo antes de confirmar que Steam Link funciona de forma estable para el uso previsto.

8. Retomar el trabajo entre sesiones

La petición «Ejecuta mi PC-Free-T4» permite indicar a un agente de desarrollo que retome el proyecto utilizando su estado documentado.

El procedimiento solicitado es el siguiente:

1. Leer "README.md", "CONTINUAR.md" y "CHANGELOG.md" de la rama "main".
2. Consultar el estado de GitHub y revisar los cambios registrados.
3. Comprobar, utilizando los medios disponibles y autorizados, si la sesión anterior sigue activa.
4. Si la sesión continúa disponible, verificar su estado antes de modificarla.
5. Si ya no existe, determinar si es posible preparar una nueva sesión conforme a las condiciones del proveedor.
6. Si hay respaldos disponibles, verificar su integridad antes de restaurar los mundos.
7. Registrar los resultados, las limitaciones encontradas y las modificaciones realizadas.

Este procedimiento no representa un mecanismo de arranque automático garantizado. Puede requerir intervención humana para seleccionar recursos, autorizar permisos, completar CAPTCHA, iniciar sesión o emparejar dispositivos. No se debe intentar eludir los mecanismos de control del proveedor.

La disponibilidad de una sesión antigua y la existencia de un respaldo son condiciones independientes. Si no existe una sesión recuperable ni un respaldo de los archivos personales, conservar el código del proyecto no permite reconstruir esos datos.

9. Mantenimiento y publicación de cambios

Los cambios realizados al proyecto deben incorporarse explícitamente al repositorio. No hay un sincronizador que supervise automáticamente la máquina remota, capture archivos del escritorio o publique modificaciones locales.

Flujo de actualización

Después de editar los archivos fuente de "scripts/":

python tools/build-notebooks.py
python tests/test_package.py

Procedimiento recomendado:

1. Revisar los cambios del código fuente.
2. Regenerar los notebooks para incorporar las modificaciones.
3. Ejecutar las pruebas del paquete.
4. Revisar el notebook generado y comprobar que no contenga datos privados, credenciales o información de conexión.
5. Distinguir los resultados reales de las funciones que solo se han preparado o probado parcialmente.
6. Actualizar "CHANGELOG.md" con los cambios técnicos de la versión.
7. Publicar los cambios en "main" después de revisar las diferencias.

Los comandos anteriores describen el flujo de mantenimiento previsto. Que una orden finalice sin errores no demuestra por sí solo que todas las funciones del entorno remoto operen correctamente.

Política del registro de cambios

Las notas de cada actualización deben centrarse en información técnica verificable:

- Cambios de implementación.
- Correcciones de errores.
- Modificaciones de configuración y dependencias.
- Cambios en el procedimiento de instalación o recuperación.
- Resultados relevantes de las pruebas.
- Limitaciones conocidas o validaciones pendientes.

No declarar una mejora de rendimiento, una recuperación satisfactoria o una función estable sin pruebas que respalden esa conclusión.

10. Seguridad y dependencias de terceros

- No publicar identificadores de conexión, contraseñas temporales, tokens, archivos de autenticación ni datos personales.
- No compartir un ZIP de respaldo sin comprobar previamente su contenido.
- No ejecutar scripts o archivos procedentes de fuentes desconocidas.
- Descargar los programas de terceros desde fuentes oficiales siempre que sea posible.
- Revisar las licencias y condiciones de los programas utilizados.
- Verificar el resultado de las transferencias antes de eliminar la única copia de un respaldo.
- Mantener las operaciones de Google Drive limitadas a las acciones necesarias para transferir los archivos seleccionados.

Los programas de terceros mantienen sus propias licencias, políticas y condiciones de uso. Este repositorio no distribuye sus binarios.

11. Estado del proyecto y limitaciones conocidas

PC-Free-T4 es un entorno experimental sujeto a las restricciones del proveedor y a cambios en las dependencias externas.

Área| Estado documentado
Preparación del entorno Linux| Basada en una configuración de referencia; su resultado depende de la sesión asignada.
Aceleración NVIDIA| Debe verificarse en cada entorno mediante las herramientas de diagnóstico.
Acceso remoto con RustDesk| Previsto como mecanismo de administración y respaldo.
Inicio de Steam y transmisión con Steam Link| En evaluación; la experiencia de juego aún debe validarse.
Corrección de Battly 3.0.1| Evita el actualizador problemático indicado para el paquete TAR de Linux.
Exportación y restauración de mundos| Preparadas y probadas con archivos ficticios; falta la validación completa con datos reales.
Copia de respaldos a Google Drive| Implementada en un notebook separado; falta la validación completa con una cuenta y una partida reales.
Persistencia de la sesión de Google Colab| No garantizada.
Recuperación de archivos personales sin respaldo| No garantizada ni asumida por el proyecto.

La condición experimental de una función debe mantenerse documentada hasta que se complete la validación correspondiente. La disponibilidad de hardware, la persistencia y la conectividad no se pueden inferir únicamente a partir de una instalación aparentemente exitosa.

---

Principio de diseño: automatizar la preparación, verificar las condiciones de ejecución, preservar los datos mediante respaldos explícitos y documentar con precisión qué se ha probado y qué permanece pendiente.
