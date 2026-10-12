<div align="center">

# ⚡ PC-Free-T4

### EXPERIMENTAL LINUX DESKTOP · NVIDIA GPU · GOOGLE COLAB

**Entorno Linux reconstruible con aceleración gráfica, acceso remoto y gestión de respaldos.**

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

![Status](https://img.shields.io/badge/STATUS-EXPERIMENTAL-orange?style=for-the-badge)
![OS](https://img.shields.io/badge/OS-Ubuntu%2024.04-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20Tesla%20T4-76B900?style=for-the-badge&logo=nvidia&logoColor=white)
![Platform](https://img.shields.io/badge/PLATFORM-Google%20Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white)

[🚀 Iniciar escritorio](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb) · [💾 Notebook de respaldos](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb) · [📋 Políticas de Colab](https://research.google.com/colaboratory/faq.html#disallowed-activities)

</div>

---

## 🧬 Descripción

**PC-Free-T4** es un proyecto experimental para reconstruir un escritorio Linux en Google Colab utilizando una configuración orientada a aplicaciones gráficas, administración remota y juegos.

| Componente | Tecnología |
|:---|:---|
| Sistema operativo | Ubuntu 24.04 |
| Escritorio | XFCE |
| GPU de referencia | NVIDIA Tesla T4 |
| Controlador observado | `580.82.07` |
| Acceso remoto | RustDesk |
| Aplicaciones | Firefox · Battly · Steam |
| Persistencia | ZIP de mundos + Google Drive |

> [!IMPORTANT]
> Este proyecto no es Windows, una imagen de disco ni una máquina persistente. Google Colab puede terminar las sesiones y la disponibilidad de una GPU T4 no está garantizada.

## 🏗️ Arquitectura

El repositorio separa los procedimientos reutilizables de los entornos de ejecución.

| Archivo / directorio | Función |
|:---|:---|
| `scripts/` | Scripts de instalación y configuración. |
| `PC-Free-T4.ipynb` | Preparación del escritorio en Google Colab. |
| `Drive-Backups.ipynb` | Transferencia de respaldos a Google Drive desde un entorno CPU. |
| `tools/build-notebooks.py` | Generación o actualización de notebooks. |
| `tests/test_package.py` | Pruebas automatizadas del paquete. |
| `CHANGELOG.md` | Historial técnico de cambios. |
| `CONTINUAR.md` | Contexto para retomar el proyecto. |

*Verifica que las rutas indicadas existan en `main` antes de publicar esta documentación.*

## ⚙️ Despliegue

### ⚡ Inicio rápido (recomendado)

[**Abrir PC-Free-T4-Rapido en Colab**](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4-Rapido.ipynb)

Selecciona **GPU T4** y pulsa **Ejecutar todo** en un entorno nuevo. Arranca solamente XFCE, aceleración gráfica y RustDesk: Firefox, Battly y Steam ya no bloquean el acceso al escritorio. La última celda permite instalarlos después, desactivados por defecto. Battly y Steam preparan primero su usuario mediante Firefox.

Se conservan las verificaciones de GPU, controlador y seguridad. La duración depende de Colab y de las descargas; no se promete un tiempo fijo. No reiniciar una sesión existente para aplicar este cambio. Usar únicamente donde las políticas del proveedor permitan escritorio remoto.

1. Lee las [condiciones oficiales de Google Colab](https://research.google.com/colaboratory/faq.html#disallowed-activities).
2. Abre `PC-Free-T4.ipynb` y selecciona una GPU compatible si está disponible y permitida.
3. Ejecuta las etapas numeradas en orden, preferiblemente en un entorno nuevo.
4. Comprueba el renderizador gráfico y revisa los errores antes de continuar.
5. Conecta el escritorio mediante RustDesk utilizando las credenciales temporales de la sesión.

### Verificación de GPU

```bash
glxinfo -B
```

El renderizador debe identificar la GPU NVIDIA esperada. Si aparece `llvmpipe`, la aceleración gráfica por hardware no está validada.

> [!WARNING]
> No fuerces versiones incompatibles del controlador ni reemplaces componentes del sistema para ignorar errores de instalación. La receta utiliza bibliotecas gráficas aisladas y debe detenerse cuando no pueda verificar las condiciones necesarias.

## 💾 Respaldos y persistencia

**GitHub conserva el código; no conserva automáticamente la sesión activa.**

La exportación documentada permite seleccionar mundos de Minecraft y generar un ZIP con un manifiesto de integridad.

| Elemento | ¿Se conserva? |
|:---|:---|
| Scripts y documentación versionados | ✅ En GitHub |
| Sesión de Colab | ❌ No garantizada |
| Mundos exportados | ✅ En el ZIP |
| Mods y configuración completa | ❌ No incluidos necesariamente |
| Cuentas y credenciales | ❌ No incluidos |

### Exportar y restaurar

1. Cierra el mundo usando **Guardar y salir**.
2. Ejecuta la celda de exportación y selecciona los mundos deseados.
3. Descarga el ZIP o transfiérelo mediante `Drive-Backups.ipynb`.
4. Para restaurar, selecciona la carpeta `saves` de la instancia correcta y ejecuta la celda correspondiente.

[![Abrir notebook de respaldos](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb)

> [!CAUTION]
> La exportación, la restauración y el flujo de Drive se han probado con archivos ficticios. Todavía no se han validado de extremo a extremo con una partida real ni con una cuenta real de Google Drive. No presupongas que existe un respaldo real hasta comprobarlo.

## 📡 Acceso remoto y streaming

RustDesk se mantiene como mecanismo de administración y conexión de respaldo.

**Steam Link continúa en evaluación.** Antes de sustituir RustDesk, deben verificarse el inicio de sesión de Steam, el emparejamiento con Android, los controles, el giro de cámara, el audio y la estabilidad durante una sesión prolongada.

La compatibilidad con un escritorio remoto no garantiza una experiencia de juego fluida.


## 🛡️ Seguridad y condiciones

- Mantén privados los identificadores y las contraseñas temporales de RustDesk.
- Descarga los programas desde fuentes oficiales.
- Verifica los ZIP antes de restaurarlos y conserva copias externas.
- No publiques tokens, credenciales ni datos personales.
- Utiliza Google Colab exclusivamente de acuerdo con sus políticas.
- Respeta las licencias y condiciones de los programas de terceros.

Los binarios de terceros no se distribuyen desde este repositorio.

---

<div align="center">

**PC-Free-T4** · Experimental environment engineering

<sub>Automatización · GPU · Linux · Persistencia verificable</sub>

</div>
