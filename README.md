# PC-Free-T4

Escritorio Ubuntu en Google Colab con GPU NVIDIA Tesla T4, entorno gráfico XFCE y transmisión mediante Selkies.

## Acceso a la VM

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yohanbit/PC-Free-T4/blob/main/PC-Free-T4.ipynb)

Pasos para iniciar el entorno virtual:

1. Abrir la libreta en Google Colab mediante el enlace anterior.
2. Configurar el entorno con GPU: **Entorno de ejecución → Cambiar tipo de entorno de ejecución → GPU T4 → Guardar**.
3. Ejecutar la libreta: **Entorno de ejecución → Ejecutar todo**.
4. Esperar a que la celda de inicio genere la URL del túnel junto con el usuario y la contraseña.
5. Abrir la URL en un navegador, ingresar las credenciales presentadas y seleccionar el botón de inicio de transmisión.

## Características

- Entorno de escritorio XFCE en Ubuntu con aceleración por hardware GPU Tesla T4.
- Transmisión de baja latencia con Selkies (NVENC H.264, WebSockets y túnel Cloudflare HTTP/2).
- Tasa de cuadros y calidad de video configurables para transmisión fluida.
- Soporte opcional para Steam, Heroic Games Launcher, Proton, Vulkan y utilidades del sistema.
- Navegador Firefox con aceleración WebGL y WebGPU.

## Notas

Las credenciales y el almacenamiento de la sesión son temporales y se reinician al cerrar la máquina virtual. Guardar los archivos necesarios externamente antes de finalizar la sesión.
