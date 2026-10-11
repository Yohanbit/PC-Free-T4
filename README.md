# PC-Free-T4 · escritorio Linux experimental con GPU

Receta y cuadernos reutilizables para reconstruir el entorno que probamos: **XFCE, NVIDIA Tesla T4, Firefox, Battly, RustDesk y Steam**. No es Windows ni una copia del disco de una máquina activa.

[![Abrir escritorio en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

[Abrir cuaderno separado de respaldos](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb)

[Condiciones oficiales](https://research.google.com/colaboratory/faq.html#disallowed-activities).

## Requisitos y alcance

La prueba utilizó Linux Ubuntu 24.04, **Tesla T4 y controlador NVIDIA 580.82.07**. Las bibliotecas gráficas se extraen aisladamente, sin reemplazar el controlador del kernel. Si el controlador cambia o desaparece la versión de los paquetes, el instalador se detiene: no forzar otra versión a ciegas.

Se necesitan al menos 8 GiB libres para comenzar; juegos y respaldos requieren espacio adicional. Los recursos y límites de Colab varían por cuenta y momento, y una T4 no está garantizada. No se activa ningún plan de pago.

## Crear una sesión

1. Leer las limitaciones y condiciones del proveedor antes de usar la receta.
2. Abrir `PC-Free-T4.ipynb`. Contiene su código integrado: no depende de acceso al repositorio durante cada etapa.
3. Si corresponde a un entorno permitido, seleccionar GPU T4 disponible sin activar pagos. Ejecutar las etapas numeradas en orden **en un entorno nuevo**, no sobre una instalación activa.
4. Comprobar que `glxinfo` informa **NVIDIA Tesla T4**, no `llvmpipe`.
5. La ventana de RustDesk muestra un ID y contraseña temporal propios de esa sesión. Mantenerlos privados. Instalar el cliente Android desde su distribución oficial y conectar.
6. Firefox, Battly y Steam tienen accesos directos. Las cuentas, el juego elegido y su versión se configuran manualmente. Steam puede tardar varios minutos en actualizarse.

El arreglo de Battly 3.0.1 omite únicamente el actualizador AppImage que se bloqueaba en el paquete TAR de Linux, conservando una copia del archivo original. **Actualizar Battly manualmente** desde una fuente oficial; no se modifica su autenticación ni la del juego.

## Qué se conserva y qué no

**GitHub conserva la receta y el historial de cambios. No conserva el entorno en ejecución.** Una nueva máquina necesita instalar los componentes otra vez, generar nuevos datos de conexión e iniciar sesión nuevamente.

El cuaderno puede quedar guardado como documento en Drive sin montar Drive en el entorno. Eso **no equivale a respaldar los archivos del escritorio**.

### Guardar partidas

1. En Minecraft, **Guardar y salir** del mundo antes de exportarlo.
2. La celda de exportación lista mundos. Seleccionar explícitamente sus índices y confirmar que se guardaron. El ZIP contiene esos mundos y un manifiesto de integridad; no copia perfiles de navegador, Steam, RustDesk ni cuentas del launcher.
3. Descargar el ZIP al celular. Se puede subir directamente con la app de Drive.
4. Alternativamente, abrir `Drive-Backups.ipynb` en **otro entorno CPU limpio**, subir el ZIP y autorizar Drive allí. Solo ese cuaderno copia el respaldo a `MyDrive/PC-Free-Backups/` y desmonta Drive. No ejecutar otras aplicaciones en ese entorno.

No configurar copias automáticas de un mundo activo: pueden quedar inconsistentes. El respaldo de esta versión incluye **mundos**, no todos los ajustes, mods o instalación completa. Para mundos modificados, conservar sus mods/versiones y usar un Minecraft compatible.

### Restaurar

Descargar el ZIP desde Drive, indicar la carpeta `saves` de la instancia correcta y usar la celda Restaurar. Comprueba rutas e integridad y crea carpetas nuevas: no sobrescribe mundos existentes. No ejecutar contenido desconocido de un respaldo ajeno.

**La exportación/restauración y el flujo Drive son funciones nuevas; se probaron con archivos ficticios, no todavía con una partida real ni con tu Drive.**


## Retomar con una petición

**«Ejecuta mi PC-Free-T4»** o **«Arranca PC-Free-T4 Debe leer primero este README, CONTINUAR.md y CHANGELOG.md en `main`, comprobar si la máquina anterior sigue viva y conservarla si existe. Si desapareció, la receta permite preparar otra sesión en un proveedor que autorice este uso y restaurar mundos desde un respaldo disponible. No es un arranque automático sin intervención: pueden hacer falta autorizaciones, CAPTCHA, login y emparejamiento del usuario.

**RustDesk es temporal:** sirve para administrar el escritorio y como conexión de respaldo, no como solución validada para jugar Minecraft. **Seguimos probando Steam Link**; primero hay que verificar el login de Steam, después emparejar Android y comprobar caminar sostenido, giro de cámara, sonido y estabilidad. Conservar RustDesk durante estas pruebas; no reemplazarlo ni cerrar la partida antes de confirmar una alternativa funcional.

La receta y los ajustes realizados están guardados; las partidas y los archivos personales solo se recuperan si se exportaron y respaldaron. No hay todavía un respaldo real verificado de la partida de esta sesión.

## Actualizaciones

Los cambios de configuración de nuestro trabajo se publicarán como commits en `main`, junto con `CHANGELOG.md` y el cuaderno regenerado. No hay un sincronizador que observe tu PC ni capture archivos automáticamente. Cambios manuales hechos por otra persona o dentro de la máquina deben revisarse e incorporarse explícitamente.

Para mantener el cuaderno actualizado tras editar `scripts/`: `python tools/build-notebooks.py`, después `python tests/test_package.py`. Publicar solo tras revisar que no hay datos privados y distinguir pruebas reales de preparación pendiente.

## Fuentes

- [RustDesk oficial](https://github.com/rustdesk/rustdesk)
- [Firefox oficial](https://www.mozilla.org/firefox/)
- [Battly oficial](https://battlylauncher.com/)
- [Steam Remote Play](https://store.steampowered.com/remoteplay)
- [Minecraft oficial](https://www.minecraft.net/)

Los programas de terceros se descargan desde sus fuentes y conservan sus propias licencias y condiciones. No se distribuyen sus binarios en este repositorio.
