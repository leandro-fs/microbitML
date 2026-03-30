---
title: Carga de firmware
description: Cómo cargar los programas en los micro:bits usando el editor web o archivos .hex
---

# Carga de firmware

Existen dos métodos para cargar el firmware de una actividad en un micro:bit V2: usando el **editor web** de MicroPython o con archivos **.hex pregenerados**.

!!! warning
    microbitML requiere **BBC micro:bit V2**. La versión V1 no es compatible.

---

## Archivos necesarios

Cada actividad requiere **dos archivos** cargados en el micro:bit:

| Archivo | Descripción |
|---|---|
| `microbitml.py` | Framework de comunicación radio y persistencia (común a todas las actividades) |
| `main.py` | Programa específico de la actividad (ej: `classquiz.py`, `perceptron.py`) |

!!! note
    Algunas actividades nombran su archivo principal de forma distinta a `main.py` (por ejemplo `classquiz.py` o `perceptron.py`). Al cargarlo en el micro:bit, debe renombrarse a `main.py` o mantener el nombre original según lo indique la documentación de cada actividad.

---

## Método 1: Editor web (recomendado)

El editor oficial de MicroPython permite escribir, editar y cargar código directamente desde el navegador.

### Pasos

1. Abrir [python.microbit.org/v/3](https://python.microbit.org/v/3) en el navegador (se recomienda Chrome)

2. Conectar el micro:bit V2 a la PC con el cable USB

3. En el editor, hacer clic en **"Project"** (panel izquierdo) para ver los archivos del proyecto

4. Agregar `microbitml.py`:
    - Clic en **"Add file"** o arrastrar el archivo al panel del proyecto
    - Verificar que aparezca listado como `microbitml.py`

5. Reemplazar el contenido de `main.py` con el código de la actividad:
    - Abrir `main.py` en el editor
    - Pegar el contenido del archivo de la actividad

6. Conectar el micro:bit al editor:
    - Clic en los tres puntos **"..."** junto al botón "Send to micro:bit"
    - Seleccionar **"Connect"**
    - Elegir el micro:bit en el diálogo del navegador

7. Clic en **"Send to micro:bit"** para flashear

!!! tip
    Si el navegador no detecta el micro:bit, verificar que se esté usando Chrome y que el micro:bit esté conectado con un cable USB que soporte datos (no solo carga).

---

## Método 2: Archivos .hex pregenerados

Para cada actividad hay un archivo `.hex` listo para usar, que incluye tanto `microbitml.py` como el programa de la actividad.

### Pasos

1. Descargar el archivo `.hex` correspondiente a la actividad:

    | Actividad | Archivo |
    |---|---|
    | mbClassquiz (alumno) | `classquiz.hex` |
    | mbClassquiz (concentrador) | `concentrador.hex` |
    | mbContador | `mbContador.hex` |
    | mbPerceptron | `perceptron.hex` |

2. Conectar el micro:bit V2 a la PC con el cable USB

3. El micro:bit aparece como una unidad USB (como un pendrive) llamada **MICROBIT**

4. Arrastrar el archivo `.hex` a la unidad **MICROBIT**

5. El LED amarillo del micro:bit parpadeará durante la carga. Cuando se detiene, la carga está completa

!!! warning
    No desconectar el micro:bit mientras el LED amarillo parpadea. Interrumpir la carga puede dejar el dispositivo en un estado inconsistente (se soluciona volviendo a flashear).

---

## Después de cargar

Una vez cargado el firmware:

1. El micro:bit se reinicia automáticamente
2. Se muestra brevemente el nombre de la actividad en los LEDs (ej: `cqz`, `cnt`, `pct`)
3. La configuración de rol y grupo se pierde y vuelve a los valores por defecto (Rol A, Grupo 1)
4. Es necesario [configurar el rol y grupo](configuracion.md) nuevamente

---

## Solución de problemas

**El micro:bit no aparece como unidad USB:**
Probar con otro cable USB. Muchos cables son solo de carga y no transmiten datos. El cable debe ser micro-B con datos.

**Error al flashear desde el editor web:**
Verificar que se esté usando Chrome. Firefox y Safari no soportan WebUSB completamente. También verificar que no haya otro programa usando el puerto serial del micro:bit (como un terminal serial abierto).

**El micro:bit muestra cara triste después de flashear:**
Indica un error en el código. Conectar un terminal serial a 115200 baud para ver el mensaje de error. Las causas comunes son: archivo `microbitml.py` faltante, error de sintaxis en `main.py`, o uso de micro:bit V1 (incompatible).

**El micro:bit no responde después de flashear:**
Mantener presionado el botón de reset (en la parte trasera del micro:bit) durante 5 segundos. Si no funciona, volver a flashear el firmware.