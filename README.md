# PC-Free-T4

Escritorio Ubuntu en Google Colab con GPU NVIDIA Tesla T4, entorno gráfico XFCE y transmisión mediante Selkies.

## Acceso a la VM

[![Abrir notebook actualizado en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/70e3269fd12493b2b3f98039d55699c559f7926a/PC-Free-T4.ipynb)


Pasos para iniciar el entorno virtual:

1. Abrir la libreta en Google Colab mediante el enlace anterior.
2. Configurar el entorno con GPU: **Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU T4 → Guardar**.
3. Ejecutar en orden: **Comprobar región → Drive: restaurar archivos y autoguardar cada 10 minutos → Cargar núcleo interno → Preparación del escritorio → Iniciar PC-Free-T4**. Autorizar Drive cuando lo solicite; la celda de Drive restaura el último respaldo completo si existe. Las demás celdas son opcionales.
4. Esperar a que la celda de inicio genere la URL del túnel junto con la cuenta y la contraseña.
5. Abrir la URL en un navegador, ingresar las credenciales presentadas y seleccionar el botón de inicio de transmisión.



## Guardado y restauración en Drive


- **Iniciar** monta Drive, restaura el último respaldo completo cuando la VM es nueva y activa el autoguardado cada 10 minutos. No bloquea la ejecución de las demás celdas.
- **Guardar ahora** realiza un respaldo manual. Cerrar juegos antes de guardar mejora la consistencia de sus archivos.
- **Listar respaldos** muestra los identificadores disponibles. Para cargar uno concreto, pegarlo en `RESPALDO` y elegir **Restaurar respaldo**; dejarlo vacío selecciona el último. Detener todos los procesos de la cuenta del escritorio antes de restaurar; se recomienda una VM nueva.
- `AUTOGUARDADO` permite activar o desactivar el guardado periódico; **Detener autoguardado** detiene el trabajador.
- Los archivos se guardan en **Mi unidad → PC-Free-T4 → backups-v2**. Se conservan los últimos **3 respaldos completos**, configurable, con verificación SHA-256. Las copias incompletas no se ofrecen para restaurar ni sustituyen a las anteriores.

Otros launchers pueden guardar juegos grandes dentro del home.


Restaurar reemplaza el home completo y deja el anterior como rescate **local**, no en Drive. Se requiere espacio local para descomprimir. Los respaldos no tienen cifrado adicional y pueden contener sesiones de aplicaciones. Una interrupción repentina puede perder los cambios posteriores al último respaldo completo. Los respaldos de formatos anteriores no se modifican ni se importan automáticamente.

Drive se monta bajo una carpeta privada distinta de `/content/drive`, para mantener intactas las comprobaciones y el aislamiento del núcleo original. Si ya existe un montaje en `/content/drive`, desmontarlo antes de iniciar el escritorio.


## Características

- Entorno de escritorio XFCE en Ubuntu con aceleración por hardware GPU Tesla T4.
- Transmisión de baja latencia con Selkies (NVENC H.264, WebSockets y túnel Cloudflare HTTP/2).
- Audio estable a 48 kHz con ganancias independientes y 90 fragmentos de cola, para evitar cortes con volumen medio/alto.
- Decodificación WebCodecs en el navegador y captura NvFBC zero-copy cuando el driver la permite, con DRI3/XShm como respaldo.
- Resolución automática de Selkies desde 960×540 inicial, con navegador Chrome 156 y perfil aislado.
- Tasa de cuadros y calidad de video configurables para transmisión fluida.
- Soporte opcional para Steam, Heroic Games Launcher, Proton, Vulkan y utilidades del sistema.
- Componentes fijados: Selkies 2.1.0, pixelflux 2.2.1, pcmflux 2.2.0, cloudflared 2026.10.3 y Chrome 156.0.8078.47-1.
- GE-Proton11-11 bajo demanda y celda de pruebas Proton de 32/64 bits con OpenGL y Vulkan.
- Instalador de `.deb`, `.AppImage`, `.tar`, `.tar.gz` y `.rpm` con descarga por URL, acceso en el escritorio y asociación de archivos.
- Chrome con aceleración WebGL y WebGPU y navegador predeterminado del escritorio.
- Heroic con Wine 9, Proton 9 y las dependencias de ejecución de juegos.
- Battly Launcher para Minecraft con Java 21, Sodium y VulkanMod opcionales.

## Notas

Las credenciales de acceso y el almacenamiento local son temporales. Sólo los respaldos completos publicados en Drive sobreviven a la pérdida de la VM; ejecutar **Guardar ahora** antes de terminar la sesión. El escritorio remoto debe utilizarse únicamente en entornos y planes que permitan este uso según las políticas de Colab.

---

## Licencia

Este proyecto se distribuye bajo la **Licencia MIT**.

> **Aviso:** Este software se entrega "tal cual", sin garantía de ningún tipo, expresa o implícita, incluidas,
pero no limitadas a, las garantías de comerciabilidad, idoneidad para un propósito particular y
no infracción. En ningún caso los autores o titulares del copyright serán responsables por
ningún reclamo, daño u otra responsabilidad, ya sea en una acción de contrato, agravio o
cualquier otra, que surja de, fuera de o en conexión con el software o el uso u otros
tratos en el software.

Ver [NOTICE](NOTICE) para la atribución completa de componentes de terceros.

---

*PC-Free-T4 — Escritorio XFCE en Colab con GPU Tesla T4. Selkies 2.1, Steam, Heroic, Battly, Proton, Chrome.*
