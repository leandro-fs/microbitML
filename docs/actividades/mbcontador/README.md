---
title: mbContador
description: Contador distribuido en base N con micro:bits — práctica de sistemas de numeración
---

# mbContador — Contador Distribuido en Base N

Actividad educativa para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

---

## ¿Qué práctica aplica esta actividad?

Sistemas de numeración. Varios micro:bits trabajan **en conjunto** como un único contador: cada dispositivo muestra un dígito del número total y se comunican entre sí por radio para propagar el "acarreo" cuando un dígito llega al límite de la base.

La base del conteo es configurable. Por defecto es **base 5** con **3 dígitos** distribuidos en 3 micro:bits.

### ¿Qué es contar en base N?

En la vida cotidiana contamos en base 10: cuando un dígito supera el 9, vuelve al 0 y el de la izquierda sube 1. En base 5, lo mismo ocurre al llegar al 5; en base 2 (binario), al llegar al 2.

| Cantidad | Base 4 | Base 5 | Hexadecimal | Binario |
|----------|--------|--------|-------------|---------|
| 0 | 0 | 0 | 0x0 | 0b0 |
| 4 | 10 | 4 | 0x4 | 0b100 |
| 5 | 11 | 10 | 0x5 | 0b101 |
| 15 | 33 | 30 | 0xF | 0b1111 |

---

## ¿Cuántos micro:bits se necesitan?

No hay una cantidad fija. Se declara con el parámetro `numberLength` en `main.py` (por defecto, **3**). Cada uno asume un rol:

| Rol | Dígito que representa |
|-----|-----------------------|
| A | Unidades (el menos significativo) |
| B | Siguiente posición |
| C | Siguiente posición |
| D | … y así sucesivamente |

Todos los micro:bits **ejecutan el mismo programa** (`main.py`). Lo único que los diferencia es el rol configurado en cada uno.

---

## Cómo usar la actividad

### 1. Cargar el programa

Cargar `mbContador.hex` (drag & drop) o cargar `main.py` junto con `microbitml.py` usando el [editor oficial](https://python.microbit.org/v/3). El código no es compatible con MakeCode.

### 2. Configurar rol y grupo en cada micro:bit

**Para entrar al modo configuración:** mantener el Pin1 conectado a GND con un cable y presionar los botones:

| Acción | Efecto |
|--------|--------|
| Pin1 + Botón A | Cambia al siguiente rol (A → B → C…) |
| Pin1 + Botón B | Cambia al siguiente grupo (1 → 2 … 9) |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales (ej. A1, B3) |

`microbitML` guarda automáticamente la configuración. Evitar el grupo 0.

### 3. Operar el contador

- **Solo el micro:bit con rol A** responde a los botones.
- **Botón A** o **Botón B** incrementa el contador en 1.
- Cuando el dígito llega a la base configurada, vuelve a 0 y envía un mensaje de radio al rol siguiente para que sume 1 (acarreo).
- Cada micro:bit muestra su dígito actual en todo momento.

!!! tip
    Para leer el número completo, mirar las pantallas de derecha a izquierda: **A** es el dígito menos significativo, **B** el siguiente, etc.

---

## Parámetros configurables en el código

Al principio de `main.py`:

```python
base = 5          # Cada dígito cuenta de 0 a (base-1)
numberLength = 3  # Cantidad de micro:bits / dígitos del contador
```

Si se cambia `base = 2`, el contador será binario. Si se cambia `numberLength = 4`, se necesitan 4 micro:bits con roles A, B, C y D.

---

## Estructura de archivos

```
mbContador/
├── main.py          ← Programa principal
├── mbContador.hex   ← Firmware precompilado
└── README.md

microbitml.py        ← Biblioteca compartida (cargar junto con main.py)
```

---

Licencia GPLv3  
(C) 2026 [Fundación Sadosky](https://fundacionsadosky.org.ar/)
