# Datos personales y recuperación

Cada persona utiliza **su propia cuenta de Google Drive** y una carpeta privada llamada `PC-Free-T4`. El proyecto no crea cuentas Google ni un Drive compartido entre usuarios. No publicar IDs de carpetas personales, archivos privados, mundos o credenciales en este repositorio.

## Qué se guarda
- Mundos de Minecraft después de Guardar y salir.
- Mods, paquetes de recursos/shaders, capturas y configuraciones de Minecraft seleccionados.
- Archivos personales adicionales elegidos explícitamente tras revisar sus carpetas.
- Una lista de archivos, tamaños y huellas SHA256 para comprobar la integridad.

La receta para instalar XFCE, NVIDIA, Selkies y las aplicaciones opcionales está en GitHub. No es necesario respaldar sus instaladores, cachés o bibliotecas descargables. No exportar perfiles completos, cuentas del launcher, tokens, cookies ni contraseñas.

## Flujo por persona
1. Autorizar su propio Drive. No reutilizar la cuenta de otra persona ni incluir una carpeta personal fija en el cuaderno público.
2. Buscar su carpeta `PC-Free-T4`; crearla si no existe. No cambiar sus permisos ni hacerla pública.
3. Revisar la máquina activa y cerrar Minecraft con Guardar y salir antes de copiar mundos. No reinstalar ni apagar el entorno para respaldarlo.
4. Exportar únicamente los datos seleccionados, descargar el archivo y subirlo a la carpeta privada mediante una conexión autorizada; alternativamente usar la app de Drive o `Drive-Backups.ipynb` en un entorno limpio separado. No montar el Drive completo en el escritorio de aplicaciones de terceros.
5. Conservar archivos fechados: no reemplazar la última copia buena. Descargar la copia de Drive y verificar SHA256 y contenido. Eso comprueba el almacenamiento, no que el mundo ya haya sido abierto de nuevo en Minecraft.
6. Antes de reconstruir, comprobar si existe una sesión activa. Si no existe, ejecutar la receta y buscar el último respaldo válido en el Drive autorizado de esa persona.
7. Revisar el contenido antes de restaurar; extraer en una carpeta nueva, sin sobreescribir mundos. Respetar versiones de Minecraft y mods. No ejecutar scripts ni archivos arbitrarios encontrados en Drive. Iniciar solamente aplicaciones conocidas de la receta, después de restaurar sus datos compatibles.

## Alcance real
Esto recupera archivos guardados, no RAM, procesos abiertos, sesiones autenticadas o una imagen completa del disco. Puede requerir login y autorización de Google en cada nueva sesión. No hay sincronización continua ni respaldo automático de cada cambio; un apagado inesperado pierde lo posterior a la última copia.

Las restricciones y límites de Colab siguen vigentes y no se eluden con este respaldo. Una descarga verificada de Drive no demuestra reconstrucción completa ni restauración jugable.
