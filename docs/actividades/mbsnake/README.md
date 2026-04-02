---
title: mbSnake
description: Juego de la viborita en la matriz LED 5×5 del micro:bit
---

# mbSnake — Juego colaborativo

Actividad para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

Escrita originalmente en Python por el estudiante **Tomate Ruso** (13ra división), durante el [curso de Robótica](https://www.cnba.uba.ar/novedades/inscripcion-al-curso-de-robotica). Ejemplo de actividad donde el framework conecta dos micro:bits en modo adversario.

---

## ¿Qué práctica aplica esta actividad?

Programación en Python con micro:bit, pensamiento computacional y lógica de juego. Clásico juego de la viborita (o los "lightcycles" de [TRON](https://es.wikipedia.org/wiki/Tron)) en la matriz LED 5×5.

---

## ¿Cuántos micro:bits se necesitan?

**2 por partida** — uno por jugador.

| Rol | Función |
|-----|---------|
| A | Jugador 1 |
| B | Jugador 2 |

---

## Cómo usar la actividad

### 1. Cargar el programa

Copiar el código de `main.py` y cargarlo junto con `microbitml.py` en el [editor oficial](https://python.microbit.org/v/3). El código no es compatible con MakeCode.

!!! note
    La emulación del editor web hace tedioso jugar porque los botones son difíciles de presionar. Se recomienda usar hardware físico.

### 2. Configurar rol y grupo

**Para entrar al modo configuración:** mantener el Pin1 conectado a GND con un cable y presionar los botones:

| Acción | Efecto |
|--------|--------|
| Pin1 + Botón A | Cambia al siguiente rol (A → B) |
| Pin1 + Botón B | Cambia al siguiente grupo (1 → 2 … 9) |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales |

### 3. Jugar

Presionar los botones para controlar la dirección de la viborita. El objetivo es no chocar con los bordes ni con la propia cola.

---

## Estructura de archivos

```
mbSnake/
├── main.py        ← Código fuente (MicroPython)
└── README.md

microbitml.py      ← Biblioteca compartida (cargar junto con main.py)
```

---

Licencia GPL v2  
(C) Tomate Ruso  
(C) [Robótica - AITEC - CNBA](https://www.cnba.uba.ar/novedades/inscripcion-al-curso-de-robotica)  
(C) 2025 [Fundación Sadosky](https://fundacionsadosky.org.ar/)
