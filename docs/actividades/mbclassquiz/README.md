---
title: mbClassquiz
description: Votación interactiva en el aula con micro:bits y ClassQuiz
---

# mbClassquiz — Votación interactiva con micro:bits

Actividad educativa para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

---

## ¿Qué práctica aplica esta actividad?

Participación en quizzes interactivos. Los alumnos usan micro:bits como dispositivos de votación físicos para responder preguntas creadas por el docente en la plataforma [ClassQuiz](https://classquiz.de/). El docente ve los resultados en tiempo real en su navegador.

---

## ¿Cuántos micro:bits se necesitan?

Se necesita **1 concentrador** (conectado por USB a la PC del docente) y **1 micro:bit por alumno** (hasta ~30).

| Rol | Función |
|-----|---------|
| A, B, C, D, E, Z | Dispositivo de alumno — navega y envía respuestas por radio |


El concentrador ejecuta un programa diferente (`concentrador.py`). Los alumnos ejecutan todos el mismo programa (`classquiz.py`).

---

## Cómo usar la actividad

### 1. Cargar el programa

**Micro:bits de alumnos:** Cargar `classquiz.hex` (drag & drop) o cargar `classquiz.py` junto con `microbitml.py` usando el [editor oficial](https://python.microbit.org/v/3).

**Micro:bit concentrador:** Cargar `concentrador.hex` o cargar `concentrador.py` junto con `microbitml.py`.

El código no es compatible con MakeCode.

### 2. Configurar rol y grupo en cada micro:bit

Cada micro:bit de alumno necesita saber qué rol tiene y a qué grupo pertenece (para no mezclarse con otras actividades en el aula).
Eso se configura según la documentación de la biblioteca `microbitML`: **Para entrar al modo configuración:** mantené el Pin1 conectado a GND con un cable y apretá los botones:

| Acción                      | Efecto                                        |
|-----------------------------|-----------------------------------------------|
| Pin1 + Botón A              | Cambia al siguiente rol (A → B → C…)          |
| Pin1 + Botón B              | Cambia al siguiente grupo (1 → 2…9)           |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales (A1, B1, etc) |

`microbitML` **guarda automáticamente** la configuración y la recuerda aunque se apague la MB.

### 3. Preparar la PC del docente

1. Conectar el micro:bit concentrador por USB a la PC
2. Ejecutar la interfaz gráfica (`python main.py` desde `Interface_grafica/`)
3. Detectar el puerto serial y conectar
4. Abrir la app ClassQuiz desde la ventana

Para instrucciones detalladas ver la guía de [instalación de Microbit-ClassQuiz](../../guias/instalacion_microbit_classquiz.md).

### 4. Operar la actividad

**Registro de alumnos:**

- Al presionar Botón A en el concentrador (o desde la interfaz web), se inicia el descubrimiento
- Los micro:bits de alumnos responden automáticamente con su ID
- El alumno ve un ✓ en pantalla cuando queda registrado

**Durante una pregunta:**

- La pantalla del alumno muestra la opción actual (A, B, C o D)
- **Botón A:** Navegar a la siguiente opción
- **Botón B:** Seleccionar/deseleccionar la opción actual
- Un punto central brillante indica que la opción está seleccionada
- En preguntas de respuesta única, seleccionar una opción deselecciona la anterior automáticamente

**Envío de respuesta:**

- La respuesta se envía automáticamente cuando el concentrador hace polling
- El alumno ve una flecha ← confirmando el envío

---

## Parámetros configurables en el código

Al principio de `classquiz.py`:

```python
ACTIVITY = "cqz"    # Nombre de la actividad (no modificar)
```

Los roles y el canal de radio están definidos dentro de la clase:

```python
roles=['A', 'B', 'C', 'D', 'E', 'Z']   # Roles disponibles
channel=0                                  # Canal de radio
```

---

## Estructura de archivos

```
mbClassquiz/
├── classquiz.py          ← Firmware alumno
├── classquiz.hex         ← Firmware alumno precompilado
├── concentrador.py       ← Firmware concentrador (gateway USB ↔ radio)
├── concentrador.hex      ← Firmware concentrador precompilado
├── Interface_grafica/    ← Programa PC (ver documentación técnica)
│   ├── main.py
│   ├── core/
│   └── apps/
└── README.md

microbitml.py             ← Biblioteca compartida (va junto con el firmware al micro:bit)
```
**Ambos archivos** (firmware + `microbitml.py`) deben cargarse en el [editor oficial de micro:bit](https://python.microbit.org/v/3/project).

---
Licencia GPLv3
(c) 2026 - [Fundación Sadosky](https://fundacionsadosky.org.ar/)