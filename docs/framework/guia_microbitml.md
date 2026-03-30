---
title: Guía de uso de microbitml
description: Radio y memoria en micro:bit con MicroPython
---

# Guía de uso de microbitml

Radio y memoria en micro:bit con MicroPython

## ¿Qué es microbitml?

microbitml es una librería-framework que simplifica la comunicación por radio entre micro:bits y el guardado de datos en memoria flash. Está compuesta por dos clases principales:

```python
from microbitml import Radio, ConfigManager

radio = Radio(activity='mi_app')       # comunicacion
config = ConfigManager(roles=['A','B'], grupos_max=4)  # memoria
```

---

## Parte 1: Comunicación por Radio

Todos los mensajes tienen la misma estructura: un nombre seguido de datos opcionales. La librería agrega automáticamente grupo y rol en todos los mensajes. El `device_id` se incluye opcionalmente con `device_id=True`.

### Objeto Message

`radio.receive()` retorna siempre un objeto `Message` con los siguientes campos:

| Campo     | Tipo    | Descripción                                                  |
|-----------|---------|--------------------------------------------------------------|
| `valid`   | bool    | `True` si el mensaje es válido para este dispositivo         |
| `act`     | str     | Actividad del mensaje recibido (hasta 5 caracteres) (prefijo antes de `:`)        |
| `name`    | str     | Nombre del comando (sin sufijos `_GR`/`_DGR`)               |
| `devID`   | str     | ID del dispositivo emisor (si usó `device_id=True`)          |
| `grp`     | int     | Grupo del emisor                                             |
| `rol`     | str     | Rol del emisor                                               |
| `valores` | list    | Lista de strings con los datos adicionales. Vacía `[]` si no hay datos |

Si el mensaje no incluye un campo, este vale `None`. `valores` siempre es una lista (vacía si no hay datos).

---

### Caso 1 — Mensaje simple (solo nombre)

Útil para comandos que no necesitan datos adicionales, como pedir que los dispositivos se identifiquen.

**EMISOR — send()**
```python
# Enviar solo un nombre de comando
radio.send("REPORT")
```

**RECEPTOR — receive()**
```python
# Recibir cualquier mensaje
msg = radio.receive()
if msg.valid:
    print(msg.name)  # 'REPORT'
```

!!! tip
    `radio.receive()` sin filtro captura cualquier mensaje. Usar `msg.name` para saber qué llegó.

---

### Caso 2 — Mensaje con filtro por tipo

Cuando solo nos interesan mensajes de un tipo específico, se pasa el nombre como filtro. Los otros mensajes son ignorados.

**EMISOR — send()**
```python
# Enviar valor numérico
radio.send("VALOR", 42)
```

**RECEPTOR — receive()**
```python
# Recibir solo mensajes 'VALOR'
msg = radio.receive('VALOR')
if msg.valid:
    num = int(msg.valores[0])
    print(num)  # 42
```

!!! tip
    `msg.valores` es una lista de strings. Siempre convertir al tipo necesario: `int()`, `str()`, etc.

El filtro también acepta una lista para escuchar múltiples tipos:
```python
msg = radio.receive(['VALOR', 'REPORT'])
```

---

### Caso 3 — Mensaje con device_id (identificación del emisor)

Se usa cuando el receptor necesita saber exactamente qué dispositivo envió el mensaje, por ejemplo para confirmar registros o responder a uno específico.

**EMISOR — send()**
```python
# Identificación completa
radio.send("ID", "cqz", device_id=True)
```

**RECEPTOR — receive()**
```python
# Acceder a todos los campos
msg = radio.receive('ID')
if msg.valid:
    print(msg.devID)       # id del emisor
    print(msg.grp)         # grupo
    print(msg.rol)         # rol
    print(msg.valores[0])  # 'cqz'
```

!!! tip
    Una vez instanciado Radio, el ID está disponible en `radio.device_id` para comparaciones:

    ```python
    radio = Radio(activity='mi_app', channel=5)
    print(radio.device_id)  # ej: 'a1b2c3d4'
    ```

---

### Caso 4 — Mensaje con grupo y rol (siempre incluido)

Grupo y rol se incluyen siempre en todos los mensajes CMD. No hace falta ningún parámetro extra. Por defecto `receive()` filtra y acepta solo mensajes del propio grupo o del grupo 0 (broadcast).

**EMISOR — send()**
```python
# Grupo y rol se incluyen siempre
radio.send("VALOR", 7)
```

**RECEPTOR — receive()**
```python
# Leer grupo, rol y valor
msg = radio.receive('VALOR')
if msg.valid:
    print(msg.grp)         # ej: 3
    print(msg.rol)         # ej: 'A'
    print(msg.valores[0])  # '7'
```

!!! tip
    Grupo y rol viven en `ConfigManager` y requieren que hayas llamado `configure()` primero:

    ```python
    # Grupo y rol viven en ConfigManager
    config.get('grupo')  # ej: 3
    config.get('role')   # ej: 'A'

    # Radio también los guarda, pero solo después de configure()
    radio.configure(group=config.get('grupo'), role=config.get('role'))
    radio.group  # '3' (string)
    radio.role   # 'A'
    ```

---

### Caso 5 — Enviar lista de valores (packed=True)

`packed=True` convierte una lista en un campo separado por comas para que no colisione con los campos de metadatos (devID, grupo, rol). El receptor ya hace el split automáticamente, por lo que `valores[]` queda indexable normalmente.

**EMISOR — send()**
```python
# Enviar lista como un solo campo
opciones = ['A', 'C']
radio.send("RESPUESTA", opciones, device_id=True, packed=True)
```

**RECEPTOR — receive()**
```python
# Recibir y separar
msg = radio.receive('RESPUESTA')
if msg.valid:
    msg.valores[0]  # 'A'
    msg.valores[1]  # 'C'
```

!!! tip
    Sin `packed`, pasar `['A','C']` como argumento directo también funciona, pero con `device_id=True` el parser los confundiría con los campos de metadatos.

---

### Caso 6 — Mensaje dirigido a un dispositivo específico

Para enviar un comando a un único dispositivo se puede enviar el id del dispositivo como mensaje. El receptor puede verificar que el device_id del mensaje coincida con el suyo.

**EMISOR — send()**
```python
# Enviar ID destino como argumento
id_destino = 'abc123'
radio.send("ACK", id_destino)
```

**RECEPTOR — receive()**
```python
# Verificar que es para mi
msg = radio.receive('ACK')
if msg.valid:
    if msg.valores[0] == radio.device_id:
        print('Soy yo!')
```

!!! tip
    `radio.device_id` contiene el ID único del dispositivo actual, generado a partir del hardware.

---

### Caso 7 — Recibir mensajes de todos los grupos (full=True)

Usado por el concentrador para escuchar mensajes de cualquier grupo, sin filtro de grupo propio.

**RECEPTOR — receive()**
```python
# El concentrador escucha todos los grupos
msg = radio.receive(full=True)
if msg.valid:
    print(msg.name)
    print(msg.grp)   # grupo del emisor (cualquiera)
    print(msg.rol)
```

!!! tip
    Por defecto `receive()` descarta mensajes de otros grupos. `full=True` desactiva ese filtro.

---

### Caso 8 — Enviar mensaje raw sin estructura CMD

`CMD=False` permite enviar un string raw directamente por radio, sin el prefijo de actividad ni la estructura de sufijos.

**EMISOR — send()**
```python
# Enviar un payload crudo
radio.send("mi_payload_custom", CMD=False)
```

!!! tip
    Útil para interoperar con otros firmwares o protocolos que no usan el formato microbitml.

---

### Caso 9 — Acceso directo al módulo radio

La instancia de Radio expone el módulo radio de MicroPython directamente a través de `self.radio`. Esto permite usar funciones del módulo nativo cuando el framework no es suficiente.

```python
from microbitml import Radio

r = Radio(activity='pct')
r.radio.config(channel=0, power=6)
```

!!! tip
    Útil para reconfigurar parámetros de radio que `configure()` no expone, como `length`, `queue` o `power`.

---

### Caso 10 — Bypass de filtro de actividad (concentrador genérico)

Por defecto, `receive()` descarta mensajes cuya actividad no coincida con la del receptor. Sin embargo, si el dispositivo está configurado en **grupo 0 y rol A**, el filtro de actividad se desactiva. Esto permite construir un concentrador genérico que reciba mensajes de cualquier actividad.

**RECEPTOR — receive()**
```python
# Concentrador genérico: grupo 0, rol A
radio = Radio(activity='con', channel=0)
# No llamar configure() — grupo 0 y rol A son los defaults

msg = radio.receive(full=True)
if msg.valid:
    print(msg.act)   # actividad del emisor (ej: 'cqz', 'cnt', 'pct')
    print(msg.name)  # nombre del comando
    print(msg.grp)   # grupo del emisor
```

!!! tip
    Combinar con `full=True` para aceptar también mensajes de cualquier grupo. El campo `msg.act` permite saber de qué actividad proviene el mensaje recibido.

!!! warning
    Este bypass solo se activa cuando `group == '0'` y `role == 'A'` (los valores por defecto de Radio). Si se llama a `configure()` con otro grupo o rol, el filtro de actividad vuelve a estar activo.

### Protocolo de radio (wire format)

Cuando se usa `send()` con `CMD=True` (default), el mensaje que viaja por radio tiene este formato:

```
actividad:NOMBRE_SUFIJO:campo1:campo2:...:datos
```

El **sufijo** determina qué campos de metadatos se incluyen:

| Sufijo | Estructura en el aire | Se genera con |
|---|---|---|
| `_GR` | `act:NOMBRE_GR:grupo:rol:datos` | `send("NOMBRE", datos)` |
| `_DGR` | `act:NOMBRE_DGR:devID:grupo:rol:datos` | `send("NOMBRE", datos, device_id=True)` |
| (sin sufijo) | `act:NOMBRE:datos` | Mensajes internos sin grupo/rol |

**Ejemplos reales:**

```
cqz:ID_DGR:a1b2c3d4:3:A:cqz       ← send("ID", "cqz", device_id=True)
cqz:REPORT_GR:0:est                ← send("REPORT") desde grupo 0, rol "est"
cnt:CARRY_GR:1:A:B                  ← send("CARRY", "B") desde grupo 1, rol A
pct:VALOR_GR:2:A:7                  ← send("VALOR", 7) desde grupo 2, rol A
```

Con `packed=True`, la lista de valores se empaqueta con comas en un solo campo:

```
cqz:ANSWER_DGR:a1b2c3d4:3:A:A,C    ← send("ANSWER", ['A','C'], device_id=True, packed=True)
```

Con `CMD=False`, el string se envía tal cual, sin prefijo de actividad ni sufijos:

```
mi_payload_custom                    ← send("mi_payload_custom", CMD=False)
```

!!! tip
    Para debuggear, conectar un micro:bit sniffer en el mismo canal con `radio.receive()` nativo y hacer `print()` del mensaje raw. El campo `RAW:` que imprime `_read()` en consola serial muestra exactamente lo que llega por el aire.

---

### Constructor de Radio

```python
radio = Radio(activity='mi_app', channel=0)
```

| Parámetro  | Tipo | Default  | Descripción                                      |
|------------|------|----------|--------------------------------------------------|
| `activity` | str  | `'mbtml'`| Prefijo de actividad (máx 5 caracteres, se trunca) |
| `channel`  | int  | `0`      | Canal de radio (0-83)                            |

Al instanciar, se activa la radio con `power=6`, `length=64`, `queue=10`.

---

### configure()

```python
radio.configure(group, role, channel=None)
```

Asigna grupo, rol y opcionalmente cambia el canal de radio.

| Parámetro | Tipo     | Descripción                                          |
|-----------|----------|------------------------------------------------------|
| `group`   | int/str  | Número de grupo                                      |
| `role`    | str      | Rol del dispositivo                                  |
| `channel` | int/None | Si se pasa, reconfigura el canal de radio            |

---

### send()

```python
radio.send(name, *args, device_id=False, packed=False, CMD=True)
```

| Parámetro   | Tipo | Default | Descripción                                  |
|-------------|------|---------|----------------------------------------------|
| `name`      | str  | —       | Nombre del comando                           |
| `*args`     | —    | —       | Datos adicionales                            |
| `device_id` | bool | `False` | Incluir ID del dispositivo en el mensaje     |
| `packed`    | bool | `False` | Empaquetar lista de args como campo único    |
| `CMD`       | bool | `True`  | `False` envía el string raw sin estructura   |

---

### receive()

```python
msg = radio.receive(filter=None, full=False)
```

| Parámetro | Tipo           | Default | Descripción                                         |
|-----------|----------------|---------|-----------------------------------------------------|
| `filter`  | str/list/None  | `None`  | Filtrar por nombre(s) de comando                    |
| `full`    | bool           | `False` | `True` acepta mensajes de cualquier grupo           |

Retorna siempre un objeto `Message`. Verificar `msg.valid` antes de usar los campos.

---

## Parte 2: Memoria con ConfigManager

ConfigManager guarda datos en la memoria flash del micro:bit. Los datos sobreviven reinicios y desconexiones. Usa un archivo de texto plano con formato `clave=valor`.

### Constructor

```python
config = ConfigManager(
    config_file='config.cfg',
    roles=['A', 'B', 'Z'],
    grupos_max=9,
    grupos_min=1,
    extra_fields={'valor': 0, 'puntaje': 0}
)
```

| Parámetro      | Tipo  | Default        | Descripción                                    |
|----------------|-------|----------------|------------------------------------------------|
| `config_file`  | str   | `'config.cfg'` | Nombre del archivo en flash                    |
| `roles`        | list  | `['A','B','Z']`| Lista de roles posibles                        |
| `grupos_max`   | int   | `9`            | Grupo máximo                                   |
| `grupos_min`   | int   | `1`            | Grupo mínimo                                   |
| `extra_fields` | dict  | `None`         | Campos personalizados adicionales a persistir  |

!!! tip
    `extra_fields` permite agregar cualquier dato extra que la app necesite persistir.

---

### Guardar, leer y modificar datos

```python
# Cargar desde flash (al iniciar)
cargado = config.load()  # retorna True si habia datos guardados

# Leer un valor
grupo = config.get('grupo')   # retorna el valor o None
rol = config.get('role')
valor = config.get('valor')   # campo extra

# Modificar un valor
config.set('valor', 5)  # solo modifica en RAM

# Guardar en flash
config.save()  # persistir todos los cambios
```

!!! warning
    `set()` solo modifica en memoria. Siempre llamar `save()` después para que el cambio sobreviva un reinicio.

!!! note
    Si la clave **no existe** en `self.config`, `set()` la ignora silenciosamente. Solo funciona con claves declaradas en `__init__` o `extra_fields`.

---

### Ciclar valores: next_role() y next_group()

```python
# Avanza al siguiente rol en la lista (cíclico)
nuevo_rol = config.next_role()    # A -> B -> Z -> A ...

# Avanza al siguiente grupo (cíclico entre grupos_min y grupos_max)
nuevo_grupo = config.next_group()  # 1 -> 2 -> ... -> 9 -> 1
```

!!! tip
    Estos métodos solo modifican en RAM. Llamar `config.save()` después si se quiere persistir.

---

### Patrón típico de uso

En casi todas las apps el flujo es: cargar al arrancar → leer para configurar el radio → modificar si cambia algo → guardar.

```python
from microbitml import Radio, ConfigManager

config = ConfigManager(roles=['A','B'], grupos_max=4, grupos_min=1)
config.load()  # recuperar datos previos

radio = Radio(activity='mi_app', channel=0)
radio.configure(
    group=config.get('grupo'),
    role=config.get('role')
)

# ... durante la app, si el usuario cambia algo:
config.set('valor', nuevo_valor)
config.save()
```

---

### Modo configuración interactiva — config_rg()

Permite que el alumno cambie grupo y rol usando botones físicos mientras mantiene pin1 tocado. Muy útil para configurar dispositivos sin conectar al PC.

```python
def mostrar():
    display.show(str(config.get('role')))
    sleep(400)
    display.show(str(config.get('grupo')))
    sleep(400)

# En el loop principal:
# Si pin1 está tocado: botón A cambia rol, botón B cambia grupo
if config.config_rg(pin1, button_a, button_b, mostrar):
    # Algo cambió, actualizar radio
    radio.configure(
        group=config.get('grupo'),
        role=config.get('role')
    )
```

!!! tip
    `config_rg()` guarda automáticamente cuando detecta un cambio. Retorna `True` si algo se modificó.

**Firma:**
```python
config.config_rg(pin, boton_a, boton_b, callback=None)
```

| Parámetro  | Descripción                                      |
|------------|--------------------------------------------------|
| `pin`      | Pin que activa el modo config (ej: `pin1`)       |
| `boton_a`  | Botón para ciclar rol                            |
| `boton_b`  | Botón para ciclar grupo                          |
| `callback` | Función opcional a ejecutar después de cada cambio |

---

### Acceder a la lista de roles

`config.roles` contiene la lista original de roles definidos al crear el ConfigManager. Útil para calcular posiciones o delays.

```python
# Ejemplo: calcular un delay proporcional al rol
config = ConfigManager(roles=['A','B','C','D'], grupos_max=9)
rol_actual = config.get('role')          # ej: 'B'
indice = config.roles.index(rol_actual)  # ej: 1
delay = indice * 500                     # 0ms, 500ms, 1000ms...
sleep(delay)
radio.send("ID", device_id=True)
```

---

## Resumen rápido

| Método | Cuándo usarlo |
|--------|---------------|
| `radio.send(nombre)` | Comando sin datos extra |
| `radio.send(nombre, valor)` | Enviar un dato numérico o texto |
| `radio.send(..., device_id=True)` | El receptor necesita saber el device_id |
| `radio.send(..., packed=True)` | Enviar una lista de valores |
| `radio.send(..., CMD=False)` | Enviar string raw sin estructura CMD |
| `radio.receive()` | Escuchar cualquier mensaje |
| `radio.receive('TIPO')` | Escuchar solo un tipo de mensaje |
| `radio.receive(['T1','T2'])` | Escuchar varios tipos de mensaje |
| `radio.receive('TIPO', full=True)` | Concentrador: escucha todos los grupos |
| `config.load()` | Al arrancar: recuperar datos guardados |
| `config.get('clave')` | Leer un valor de configuración |
| `config.set('clave', valor)` | Modificar un valor en RAM |
| `config.save()` | Persistir en flash tras un `set()` |
| `config.next_role()` | Avanzar al siguiente rol (cíclico) |
| `config.next_group()` | Avanzar al siguiente grupo (cíclico) |
| `config.config_rg(...)` | Permitir cambio de grupo/rol con botones |