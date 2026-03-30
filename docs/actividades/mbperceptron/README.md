---
title: mbNombreActividad
description: Breve descripción de una línea
---

# mbNombreActividad — Título Descriptivo

Actividad educativa para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

---

## ¿Qué práctica aplica esta actividad?

(Describir qué tema o concepto se trabaja con esta actividad)

---

## ¿Cuántos micro:bits se necesitan?

(Cantidad y qué rol cumple cada uno)

| Rol | Función |
|-----|---------|
| A   |         |
| B   |         |

Todos los micro:bits ejecutan el mismo programa (`main.py`). Lo único que los diferencia es el rol configurado en cada uno.

---

## Cómo usar la actividad

### 1. Cargar el programa

Podés probar la actividad ya compilada cargando el archivo `mbNombre.hex` en varias micro:bit o el editor oficial: [python.microbit.org](https://python.microbit.org). El **mismo programa** corre en todos los micro:bits del aula (los roles y grupos se configuran en tiempo de ejecución).
Para editar, cargá el archivo `main.py` junto con `microbitml.py` usando el editor oficial: [python.microbit.org](https://python.microbit.org). El código no es compatible con MakeCode.

### 2. Configurar rol y grupo en cada micro:bit

Cada micro:bit necesita saber qué rol tiene y a qué grupo pertenece (para no mezclarse con otras actividades en el aula).
Eso se configura según la documentación de la biblioteca `microbitML`: **Para entrar al modo configuración:** mantené el Pin1 conectado a GND con un cable y apretá los botones:

| Acción                      | Efecto                                        |
|-----------------------------|-----------------------------------------------|
| Pin1 + Botón A              | Cambia al siguiente rol (A → B → C…)          |
| Pin1 + Botón B              | Cambia al siguiente grupo (1 → 2…9)           |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales (A1, B1, etc) |

`microbitML` **guarda automáticamente** la configuración y la recuerda aunque se apague la MB.

### 3. Operar la actividad

(Describir cómo se usa: qué hacen los botones, qué se ve en pantalla, cómo interactúan los micro:bits)

---

## Parámetros configurables en el código

(Si aplica, listar las variables que se pueden modificar al principio de `main.py`)

```python
# ejemplo:
# variable = valor   # Descripción
```

---

## Estructura de archivos

```
mbNombreActividad/
├── main.py              ← Programa principal
├── mbNombre.hex         ← Firmware precompilado
└── README.md

microbitml.py            ← Biblioteca compartida (va junto con main.py al micro:bit)
```
**Ambos archivos** deben cargarse en el [editor oficial de micro:bit](https://python.microbit.org/v/3/project).

---
Licencia GPLv3
(c) 2026 - [Fundación Sadosky](https://fundacionsadosky.org.ar/)