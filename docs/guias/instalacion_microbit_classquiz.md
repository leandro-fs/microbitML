---
title: Instalación de Microbit-ClassQuiz
description: Requisitos y pasos de instalación del programa PC que conecta los micro:bits con ClassQuiz
---

# Instalación de Microbit-ClassQuiz

Esta guía cubre la instalación del entorno necesario para trabajar con microbitML: el editor web para programar los micro:bits y el programa PC que los conecta con la plataforma ClassQuiz.

---

## Requisitos de hardware

- **BBC micro:bit V2** (la versión V1 no es compatible)
- Cable USB micro-B para conectar el micro:bit a la PC
- Cable cocodrilo o jumper para conectar Pin1 a GND (configuración de rol/grupo)

---

## 1. Editor web de micro:bit

El editor oficial de MicroPython para micro:bit es la herramienta principal para escribir y cargar código en los dispositivos.

**Acceso:** [https://python.microbit.org/v/3](https://python.microbit.org/v/3)

No requiere instalación. Funciona en cualquier navegador moderno (Chrome, Firefox, Edge). Se recomienda Chrome por mejor soporte de WebUSB.

!!! note
    El editor web permite cargar múltiples archivos al micro:bit. Para las actividades de microbitML siempre se necesitan al menos dos archivos: `microbitml.py` y el `main.py` de la actividad.

---

## 2. Python para PC (interfaz gráfica)

La interfaz gráfica que conecta los micro:bits con la plataforma ClassQuiz requiere Python instalado en la PC del docente.

### Requisitos

- **Python 3.12 o superior**
- **pip** (viene incluido con Python)
- **Tkinter** (viene incluido con Python en Windows; en Linux puede requerir instalación separada)

### Windows

1. Descargar Python desde [python.org/downloads](https://www.python.org/downloads/)
2. Durante la instalación, marcar la opción **"Add Python to PATH"**
3. Verificar la instalación:

```powershell
python --version
pip --version
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-tk
```

### Instalación del proyecto

```bash
# Clonar el repositorio
git clone https://github.com/leandro-fs/microbitML
cd microbitML/mbClassquiz/Interface_grafica

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias principales

El archivo `requirements.txt` contiene las siguientes librerías:

| Librería | Función |
|---|---|
| `pyserial` | Comunicación USB serial con el concentrador micro:bit |
| `Flask` + `Flask-SocketIO` | Servidor web local para la interfaz |
| `python-socketio[client]` | Cliente Socket.IO para conectar con ClassQuiz |
| `python-engineio` | Motor de transporte para Socket.IO |
| `requests` | Peticiones HTTP |
| `websocket-client` | Transporte WebSocket |

### Ejecutar la interfaz

```bash
# Con el entorno virtual activado
python main.py
```

Se abrirá la ventana de **Microbit Proxy** con los controles de conexión USB y selección de actividad.

!!! warning
    En Windows, el puerto serial del micro:bit aparece como `COMx`. En Linux aparece como `/dev/ttyACMx`. Si el puerto no aparece, verificar que el micro:bit esté conectado y que el driver USB esté instalado.

---

## Verificación rápida

Una vez instalado todo, verificar que cada componente funciona:

| Componente | Verificación |
|---|---|
| Editor micro:bit | Abrir [python.microbit.org](https://python.microbit.org/v/3) en el navegador |
| Python PC | Ejecutar `python main.py` desde `Interface_grafica/` |
| micro:bit conectado | El puerto serial aparece en la interfaz gráfica al presionar "Detectar" |

!!! tip
    Para la instalación del servidor ClassQuiz self-hosted, consultar la guía [Instalación de ClassQuiz](instalacion_classquiz.md).