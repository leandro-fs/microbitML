# mbContador — Contador Distribuido en Base N

Actividad educativa para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

---

## ¿Qué práctica aplica esta actividad?

Practicaremos Sistemas de numeración.   

Varios micro:bits trabajan **en conjunto** como un único contador. Cada dispositivo muestra un dígito del número total, y se comunican entre sí por radio cuando necesitan "avisarle" al siguiente que avance.

La base del conteo es configurable. Por defecto es **base 5** (dígitos del 0 al 4), con un número de **3 dígitos** distribuidos en 3 micro:bits.

### ¿Qué es contar en base N?

En la vida cotidiana contamos en base 10: cuando un dígito supera el 9, vuelve al 0 y el de la izquierda sube 1. En base 5, lo mismo ocurre al llegar al 5. En base 4, al llegar al 4.    
Ejemplos de cantidades (base10), escritas en otras bases:

| Cantidad  | Base_4 | Base_5 | Hexadecimal | Binario   |
|-----------|--------|--------|-------------|-----------|
| 0         | 0      | 0      | 0x0         | 0b0       |
| 1         | 1      | 1      | 0x1         | 0b1       |
| 3         | 3      | 3      | 0x3         | 0b11      |
| 4         | 10     | 4      | 0x4         | 0b100     |
| 5         | 11     | 10     | 0x5         | 0b101     |
| 8         | 20     | 13     | 0x8         | 0b1000    |
| 15        | 33     | 30     | 0xF         | 0b1111    |

---

## ¿Cuántos micro:bits se necesitan?

No hay una cantidad mandatoria. Se declara con el parámetro `numberLength` definido en `main.py` (por defecto, **3**). Cada uno asume un **rol**:

| Rol | Dígito que representa     |
|-----|---------------------------|
| A   | Unidades (el más pequeño) |
| B   | Siguiente posición        |
| C   | Siguiente posición        |
| D   | ... y así sucesivamente   |

Todos los micro:bits **ejecutan el mismo programa** (`main.py`). Lo único que los diferencia es el rol configurado en cada uno.

---

## Cómo usar la actividad

### 1. Cargar el programa

Podés probar la actividad ya compilada cargando el archivo `mbContador.hex` en varias micro:bit o el editor oficial: [python.microbit.org](https://python.microbit.org). El **mismo programa** corre en todos los micro:bits del aula (los roles y grupos se configuran en tiempo de ejecución)
Para editar, cargá el archivo `main.py` junto con `microbitml.py` usando el editor oficial: [python.microbit.org](https://python.microbit.org). El código no es compatible con MakeCode. 

### 2. Configurar rol y grupo en cada micro:bit

Cada micro:bit necesita saber qué rol tiene y a qué grupo pertenece (para no mezclarse con otras actividades en el aula).
Eso se configura según la documentación de la biblioteca `microbitML`:  **Para entrar al modo configuración:** mantené el Pin1 conectado a GND con un cable y apretá los botones:

| Acción                      | Efecto                                        |
|-----------------------------|-----------------------------------------------|
| Pin1 + Botón A              | Cambia al siguiente rol (A → B → C…)          |
| Pin1 + Botón B              | Cambia al siguiente grupo (1 → 2…9)           |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales (A1, B1, etc) |

`microbitML` **guarda automáticamente** la configuración y la recuerda aunque se apague la MB.

### 3. Operar el contador

- **Solo el micro:bit con rol A** responde a los botones.
- Presionar **botón A** o **botón B** incrementa el contador en 1.
- Cuando el dígito llega a la base configurada, vuelve a 0 y envía un mensaje de radio al micro:bit del siguiente rol para que él también sume 1.
- Cada micro:bit muestra su dígito actual en pantalla en todo momento.
- Para leer el número completo, mirá las pantallas de derecha a izquierda: **A** es el dígito menos significativo, **B** el siguiente, etc.

---

## Parámetros configurables en el código

Al principio de `main.py` encontrás estas dos variables que podés modificar:

```python
base = 5          # Cada dígito cuenta de 0 a (base-1)
numberLength = 3  # Cantidad de micro:bits / dígitos del contador
```

Si cambiás `base = 4`, el contador será en base 4. Si cambiás `numberLength = 4`, necesitás 4 micro:bits con roles A, B, C y D.

---

## La biblioteca microbitML

[microbitML](https://github.com/leandro-fs/microbitML) (`microbitml.py`) es la biblioteca que hace posible la comunicación entre micro:bits y la gestión de las actividades grupales. Provee dos clases principales:

### `Radio` — Comunicación entre dispositivos

Se encarga de enviar y recibir mensajes por radio de forma estructurada, filtrando automáticamente los mensajes que no corresponden a esta actividad o a este grupo.

**Cómo se usa en mbContador:**

```python
self.radio = mbml.Radio(activity="cnt", channel=0)
self.radio.configure(group=grupo, role=rol)

# Enviar un "aviso de carry" al siguiente dígito:
self.radio.send("CARRY", rol_siguiente)

# Recibir mensajes:
message = self.radio.receive()
if message.valid and message.name == 'CARRY':
    # procesar el carry
```

Cada mensaje viaja con el nombre de la actividad, el grupo y el rol del emisor, lo que permite que varios grupos trabajen en el aula al mismo tiempo sin interferirse.

**Campos del objeto `Message` que devuelve `receive()`:**

| Campo        | Contenido                                      |
|--------------|------------------------------------------------|
| `valid`      | `True` si el mensaje es válido para este dispositivo |
| `name`       | Nombre del comando recibido (ej. `"CARRY"`)    |
| `grp`        | Grupo del emisor                               |
| `rol`        | Rol del emisor                                 |
| `valores`    | Lista de parámetros adicionales del mensaje    |

### `ConfigManager` — Persistencia de la configuración

Guarda y recupera el rol y el grupo de cada micro:bit en un archivo interno (`config.cfg`), de modo que la configuración sobrevive a los reinicios.

**Cómo se usa en mbContador:**

```python
self.config = mbml.ConfigManager(
    roles=roles,      # Lista de roles posibles, ej. ('A', 'B', 'C')
    grupos_max=9,
    grupos_min=1
)
self.config.load()           # Carga la config guardada
self.config.get('role')      # Obtiene el rol actual
self.config.get('grupo')     # Obtiene el grupo actual
self.config.save()           # Guarda la config
```

El método `config_rg(pin1, boton_a, boton_b, callback)` gestiona el modo configuración: detecta si el logo está siendo tocado y, en ese caso, interpreta los botones como cambios de rol o grupo en lugar de acciones del juego.

---

## Estructura de archivos

```
mbContador/
└── main.py          ← Programa principal (este archivo)

microbitml.py        ← Biblioteca compartida (va junto con main.py al micro:bit)
```
**Ambos archivos** deben cargarse en el [editor oficial de micro:bit](https://python.microbit.org/v/3/project).

---
Licencia GPLv3   
(C) 2026 [Fundación Sadosky](https://fundacionsadosky.org.ar/)