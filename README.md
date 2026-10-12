# PC-Free-T4

Escritorio Ubuntu con NVIDIA Tesla T4, XFCE y acceso desde Chrome mediante Selkies.

## Iniciar

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

1. Abrir el cuaderno.
2. **Entorno de ejecución → Cambiar tipo de entorno → GPU T4 → Guardar.**
3. **Entorno de ejecución → Ejecutar todo.** Usar una VM nueva.
4. Esperar a que Colab muestre **URL, usuario y contraseña**.
5. Abrir esa URL en Chrome, introducir las credenciales y pulsar **Jugar**. Aceptar los permisos de pantalla completa y controles.

[Inicio rápido](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4-Rapido.ipynb) · [Respaldos manuales](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/Drive-Backups.ipynb)

## Perfil incluido

- **720p, 60 FPS objetivo, H.264/NVENC, Turbo y CBR 5 Mbps.** FPS/bitrate ajustables; 60 FPS no garantizados.
- OpenGL/Vulkan y EGL NVIDIA con bibliotecas de la versión exacta del controlador.
- Firefox con WebRender/WebGL y perfil independiente. Descarga en segundo plano, sin abrir ventanas.
- Archivos, Descargas, Terminal y audio preparados.
- Protección del clic derecho sobre la transmisión. Gaming Mode solicita ratón relativo y bloqueo de teclado.
- Preparación de **Flatpak/Sober** en segundo plano. Comprueba SSE4.1, kernel y sandbox antes de descargar runtimes.


**Android:** si el sistema convierte el clic derecho en Atrás, cambiar la asignación del ratón a clic derecho/menú contextual, si existe. La web no puede interceptar eventos que Android consume. Las teclas reservadas como Win/Alt+Tab tampoco están garantizadas.


[Compatibilidad y controles](COMPATIBILIDAD.md) · [Diagnóstico](CONTINUAR.md) · [Cambios](CHANGELOG.md)

## Notas

Las credenciales y el disco son temporales. No guardar salidas del cuaderno ni compartir el acceso. Exportar archivos antes de cerrar la VM.

