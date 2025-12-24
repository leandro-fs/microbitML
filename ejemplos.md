# Guía del Desarrollador - microbitcore.py

## Introducción

microbitcore.py es una librería para simplificar la comunicación radio entre micro:bits. Proporciona dos clases principales:

- **RadioMessage**: Manejo de mensajes por radio
- **ConfigManager**: Persistencia de configuración

---

## RadioMessage - Comunicación Radio

### Inicialización básica

**Cuándo usar**: Primer paso obligatorio para cualquier proyecto que use comunicación radio entre micro:bits.

```python
from microbit import *
import radio
from microbitcore import RadioMessage

# Inicializar radio
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# Crear handler de mensajes (formato comando)
msg = RadioMessage(format="command")
```

### Formato CSV vs Command

**Cuándo usar CSV**: Cuando necesitas filtrar mensajes por grupo/rol automáticamente.
**Cuándo usar Command**: Para protocolos flexibles con comandos personalizados (recomendado para mayoría de casos).

**Formato CSV**: `grupo,rol,payload`

```python
msg_csv = RadioMessage(format="csv", device_id="abc123")
msg_csv.set_context(group=1, role="A")

# Enviar mensaje CSV
msg_csv.send(radio.send, "HOLA")
# Radio transmite: "1,A,HOLA"
```

**Formato Command**: `CMD:arg1:arg2:...`

```python
msg_cmd = RadioMessage(format="command", device_id="abc123")

# Enviar comando
msg_cmd.send(radio.send, "PING:abc123")
# Radio transmite: "PING:abc123"
```

### Enviar mensajes

```python
# Enviar texto simple
msg.send(radio.send, "HOLA")

# Usar comandos predefinidos
msg.send(radio.send, msg.cmd_report())  # "REPORT"
msg.send(radio.send, msg.cmd_ping("device123"))  # "PING:device123"
```

### Recibir mensajes

```python
# Leer mensaje del radio
resultado = msg.receive(radio.receive)

if resultado:
    tipo = resultado['t']   # Tipo de mensaje
    data = resultado['d']   # Datos completos
    
    if tipo == 'PING':
        # Procesar PING
        pass
```

### Ejemplo completo: Eco simple

**Cuándo usar**: Validar que la comunicación radio funciona. Útil para debugging básico de conectividad entre dispositivos.

```python
from microbit import *
import radio
from microbitcore import RadioMessage

radio.config(channel=7)
radio.on()

msg = RadioMessage(format="command")

while True:
    # Recibir
    resultado = msg.receive(radio.receive)
    
    if resultado and resultado['t'] == 'ECHO':
        # Extraer payload
        tipo, args = msg.parse_payload(resultado['d'])
        texto = args[0] if args else ""
        
        # Responder
        msg.send(radio.send, "RESPUESTA:{}".format(texto))
        display.show(Image.YES)
        sleep(500)
        display.clear()
    
    sleep(50)
```

---

## Comandos Predefinidos

### cmd_report()

**Cuándo usar**: Broadcast inicial para que todos los dispositivos se identifiquen. Típico en fase de descubrimiento.

Broadcast para descubrimiento de dispositivos.

```python
# Concentrador
msg.send(radio.send, msg.cmd_report())  # "REPORT"

# Classquiz
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'REPORT':
    # Responder con ID
    msg.send(radio.send, msg.cmd_id())
```

### cmd_id()

Identificación de dispositivo.

```python
# Requiere device_id en constructor
msg = RadioMessage(format="command", device_id="abc123")

msg.send(radio.send, msg.cmd_id())  # "ID:abc123"
```

### cmd_ack(target_id)

**Cuándo usar**: Confirmar al dispositivo que fue registrado exitosamente después de cmd_id() o cmd_report().

Confirmar recepción.

```python
# Concentrador confirma registro
msg.send(radio.send, msg.cmd_ack("abc123"))  # "ACK:abc123"

# Classquiz verifica si es para él
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'ACK':
    if msg.is_for_me(resultado['d']):
        display.show(Image.YES)
```

### cmd_ping(target_id) / cmd_pong()

**Cuándo usar**: Verificar si un dispositivo específico sigue conectado antes de enviarle comandos críticos.

Verificar conectividad.

```python
# Concentrador
msg.send(radio.send, msg.cmd_ping("abc123"))  # "PING:abc123"

# Classquiz
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'PING':
    if msg.is_for_me(resultado['d']):
        msg.send(radio.send, msg.cmd_pong())  # "PONG:abc123"
```

### cmd_poll(target_id)

**Cuándo usar**: Solicitar respuesta activa de un dispositivo específico, como en sistemas de votación o recolección de datos.

Solicitar respuesta.

```python
# Concentrador
msg.send(radio.send, msg.cmd_poll("abc123"))  # "POLL:abc123"

# Classquiz
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'POLL':
    if msg.is_for_me(resultado['d']):
        # Enviar respuesta
        pass
```

### cmd_answer(*opciones)

**Cuándo usar**: Responder a cmd_poll() con una o múltiples opciones seleccionadas (ej: votación, quiz, formularios).

Responder con opciones seleccionadas.

```python
# Classquiz responde
msg.send(radio.send, msg.cmd_answer("A"))  # "ANSWER:abc123:A"
msg.send(radio.send, msg.cmd_answer("A", "B", "C"))  # "ANSWER:abc123:A,B,C"
```

### cmd_qparams(tipo, num_opciones)

**Cuándo usar**: Broadcast de configuración de pregunta antes de iniciar votación para sincronizar todos los dispositivos.

Enviar parámetros de pregunta.

```python
# Concentrador
msg.send(radio.send, msg.cmd_qparams("unica", 4))  # "QPARAMS:unica:4"

# Classquiz
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'QPARAMS':
    tipo, num = msg.extract_qparams(resultado['d'])
    # tipo = "unica", num = 4
```

### command(cmd, *args)

**Cuándo usar**: Cuando los comandos predefinidos no cubren tu caso de uso. Permite crear protocolos personalizados.

Crear comandos personalizados.

```python
# Crear comando custom
cmd = msg.command("CUSTOM", "arg1", "arg2", 123)
msg.send(radio.send, cmd)  # "CUSTOM:arg1:arg2:123"
```

---

## Métodos de Extracción

### parse_payload(mensaje)

**Cuándo usar**: Primer paso para procesar cualquier mensaje recibido. Separa comando de argumentos para análisis manual.

Divide mensaje en tipo y argumentos.

```python
mensaje = "PING:abc123"
tipo, args = msg.parse_payload(mensaje)
# tipo = "PING"
# args = ["abc123"]

mensaje = "ANSWER:dev123:A,B,C"
tipo, args = msg.parse_payload(mensaje)
# tipo = "ANSWER"
# args = ["dev123", "A,B,C"]
```

### is_for_me(mensaje)

**Cuándo usar**: Filtrar mensajes dirigidos específicamente a este dispositivo, ignorando broadcasts o mensajes para otros.

Verifica si mensaje es para este dispositivo.

```python
msg = RadioMessage(format="command", device_id="abc123")

mensaje1 = "PING:abc123"
mensaje2 = "PING:xyz789"

msg.is_for_me(mensaje1)  # True
msg.is_for_me(mensaje2)  # False
```

### extract_device_id(mensaje)

Extrae device_id del primer argumento.

```python
mensaje = "ACK:abc123"
device_id = msg.extract_device_id(mensaje)
# device_id = "abc123"
```

### extract_answer(mensaje)

Extrae device_id y opciones de respuesta.

```python
mensaje = "ANSWER:abc123:A,B,C"
device, opciones = msg.extract_answer(mensaje)
# device = "abc123"
# opciones = ["A", "B", "C"]
```

### extract_qparams(mensaje)

Extrae parámetros de pregunta.

```python
mensaje = "QPARAMS:multiple:3"
tipo, num = msg.extract_qparams(mensaje)
# tipo = "multiple"
# num = 3
```

---

## Ejemplo: Sistema Ping-Pong

**Cuándo usar**: Descubrir dispositivos activos en la red o verificar conectividad punto a punto antes de tareas complejas.

### Dispositivo A (inicia ping)

```python
from microbit import *
import radio
import machine
from microbitcore import RadioMessage

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

radio.config(channel=7)
radio.on()

msg = RadioMessage(format="command", device_id=device_id)

while True:
    if button_a.was_pressed():
        # Enviar PING broadcast
        msg.send(radio.send, "PING:broadcast")
        display.show(Image.ARROW_E)
    
    # Escuchar PONGs
    resultado = msg.receive(radio.receive)
    if resultado and resultado['t'] == 'PONG':
        remote_id = msg.extract_device_id(resultado['d'])
        display.scroll(remote_id[:4], delay=60)
    
    sleep(50)
```

### Dispositivo B (responde pong)

```python
from microbit import *
import radio
import machine
from microbitcore import RadioMessage

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

radio.config(channel=7)
radio.on()

msg = RadioMessage(format="command", device_id=device_id)

while True:
    resultado = msg.receive(radio.receive)
    
    if resultado and resultado['t'] == 'PING':
        # Responder PONG
        msg.send(radio.send, msg.cmd_pong())
        display.show(Image.ARROW_W)
        sleep(300)
        display.clear()
    
    sleep(50)
```

---

## ConfigManager - Persistencia

### Inicialización

**Cuándo usar**: Al inicio del programa para crear configuración persistente que sobrevive reinicios del micro:bit.

```python
from microbitcore import ConfigManager

# Configuración simple
config = ConfigManager(
    config_file='config.cfg',
    roles=['A', 'B', 'C'],
    grupos_max=9
)

# Con campos extra
config = ConfigManager(
    config_file='vote.cfg',
    roles=[],
    extra_fields={'opcion': None, 'confirmada': False}
)
```

### Cargar y guardar

**Cuándo usar**: load() al inicio para recuperar valores previos, save() después de cada cambio importante para persistir.

```python
# Cargar (crea archivo si no existe)
config.load()

# Modificar
config.set('role', 'B')
config.set('grupo', 3)

# Guardar
config.save()
```

### Obtener valores

```python
role = config.get('role')
grupo = config.get('grupo')

# Todos los valores
todos = config.get_all()
# {'role': 'B', 'grupo': 3}
```

### Ciclar valores

**Cuándo usar**: Para cambiar rol/grupo con botones sin hardcodear valores. Ideal para interfaces de usuario simples.

```python
# Ciclar rol: A -> B -> C -> A
config.cycle_role()

# Ciclar grupo: 0 -> 1 -> ... -> 9 -> 0
config.cycle_grupo()
```

### Resetear configuración

```python
# Volver a valores por defecto
config.reset()
# role = 'A', grupo = 0, campos extra = None
```

---

## Ejemplo: Configuración Persistente

**Cuándo usar**: Cuando cada dispositivo necesita recordar su identidad (grupo, rol, puntos) entre reinicios sin reprogramar.

```python
from microbit import *
from microbitcore import ConfigManager

# Crear config con campos personalizados
config = ConfigManager(
    config_file='my_config.cfg',
    roles=['A', 'B', 'C', 'D'],
    grupos_max=5,
    extra_fields={'nombre': 'default', 'puntos': 0}
)

# Cargar config anterior (si existe)
config.load()

while True:
    # Pin1: cambiar rol
    if pin1.is_touched():
        config.cycle_role()
        config.save()
        display.show(config.get('role'))
        sleep(1000)
        display.clear()
    
    # Pin2: cambiar grupo
    if pin2.is_touched():
        config.cycle_grupo()
        config.save()
        display.show(str(config.get('grupo')))
        sleep(1000)
        display.clear()
    
    # Botón A: incrementar puntos
    if button_a.was_pressed():
        puntos = config.get('puntos')
        config.set('puntos', puntos + 1)
        config.save()
        display.scroll(str(puntos + 1))
    
    # Botón B: mostrar todo
    if button_b.was_pressed():
        display.scroll("R:" + config.get('role'))
        sleep(500)
        display.scroll("G:" + str(config.get('grupo')))
        sleep(500)
        display.scroll("P:" + str(config.get('puntos')))
    
    sleep(100)
```

---

## Ejemplo: Votación Simple

**Cuándo usar**: Sistema básico donde un concentrador recolecta respuestas de múltiples Classquizs en tiempo real.

### Concentrador

```python
from microbit import *
import radio
from microbitcore import RadioMessage

radio.config(channel=7)
radio.on()

msg = RadioMessage(format="command")
votos = {}

while True:
    if button_a.was_pressed():
        # Enviar parámetros de pregunta
        msg.send(radio.send, msg.cmd_qparams("unica", 4))
        display.show(Image.ARROW_E)
        sleep(2000)
        
        # Solicitar votos
        msg.send(radio.send, "POLL:ALL")
        display.show(Image.ASLEEP)
    
    # Recibir respuestas
    resultado = msg.receive(radio.receive)
    if resultado and resultado['t'] == 'ANSWER':
        device, opciones = msg.extract_answer(resultado['d'])
        votos[device] = opciones[0] if opciones else ""
        display.scroll(len(votos), delay=60)
    
    sleep(50)
```

### Classquiz

```python
from microbit import *
import radio
import machine
from microbitcore import RadioMessage, ConfigManager

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

radio.config(channel=7)
radio.on()

msg = RadioMessage(format="command", device_id=device_id)

vote_config = ConfigManager(
    config_file='vote.cfg',
    extra_fields={'tipo': None, 'num_opciones': 4, 'opcion': None}
)
vote_config.load()

opciones = ['A', 'B', 'C', 'D']
idx = 0

while True:
    # Recibir parámetros
    resultado = msg.receive(radio.receive)
    
    if resultado and resultado['t'] == 'QPARAMS':
        tipo, num = msg.extract_qparams(resultado['d'])
        vote_config.set('num_opciones', num)
        vote_config.save()
        display.show(Image.YES)
    
    # Responder a POLL
    elif resultado and resultado['t'] == 'POLL':
        opcion = vote_config.get('opcion')
        if opcion:
            msg.send(radio.send, msg.cmd_answer(opcion))
            display.show(Image.ARROW_W)
    
    # Navegar opciones
    if button_a.was_pressed():
        num = vote_config.get('num_opciones')
        idx = (idx + 1) % num
        vote_config.set('opcion', opciones[idx])
        vote_config.save()
        display.show(opciones[idx])
    
    sleep(50)
```

---

## Comandos Personalizados con Grupo:Rol

**Cuándo usar**: Para sistemas organizados por mesas/equipos donde necesitas direccionar por grupo:rol en vez de device_id.

### Extender funcionalidad

```python
from microbitcore import RadioMessage

msg = RadioMessage(format="command", device_id="abc123")

# Crear comandos personalizados usando command()
def cmd_id_with_group(device_id, grupo, rol):
    return msg.command("ID", device_id, grupo, rol)

def cmd_poll_group(grupo, rol):
    return msg.command("POLL", grupo, rol)

def cmd_answer_with_group(device_id, grupo, rol, opcion):
    return msg.command("ANSWER", device_id, grupo, rol, opcion)

# Usar
msg.send(radio.send, cmd_id_with_group("abc123", 1, "A"))
# Radio: "ID:abc123:1:A"

msg.send(radio.send, cmd_poll_group(3, "B"))
# Radio: "POLL:3:B"

msg.send(radio.send, cmd_answer_with_group("abc123", 3, "B", "C"))
# Radio: "ANSWER:abc123:3:B:C"
```

### Parsear comandos custom

```python
def extract_id_with_group(msg_obj, mensaje):
    tipo, args = msg_obj.parse_payload(mensaje)
    if tipo != 'ID' or len(args) < 3:
        return (None, None, None)
    
    device_id = args[0]
    grupo = int(args[1])
    rol = args[2]
    return (device_id, grupo, rol)

def extract_answer_with_group(msg_obj, mensaje):
    tipo, args = msg_obj.parse_payload(mensaje)
    if tipo != 'ANSWER' or len(args) < 4:
        return (None, None, None, [])
    
    device_id = args[0]
    grupo = int(args[1])
    rol = args[2]
    opciones = args[3].split(',') if ',' in args[3] else [args[3]]
    return (device_id, grupo, rol, opciones)

# Usar
resultado = msg.receive(radio.receive)
if resultado and resultado['t'] == 'ID':
    device_id, grupo, rol = extract_id_with_group(msg, resultado['d'])
    print("Device: {} Grupo: {} Rol: {}".format(device_id, grupo, rol))
```

---

## Buenas Prácticas

### 1. Siempre verificar resultados

```python
resultado = msg.receive(radio.receive)
if resultado:  # Puede ser None
    if resultado['t'] == 'ESPERADO':
        # Procesar
        pass
```

### 2. Usar device_id único

```python
import machine

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
msg = RadioMessage(format="command", device_id=device_id)
```

### 3. Cargar config al inicio

```python
config = ConfigManager(config_file='config.cfg')
config.load()  # Carga valores previos

# Si falla, usa valores por defecto
if config.get('grupo') == 0:
    config.set('grupo', 1)
    config.save()
```

### 4. Guardar después de cambios importantes

```python
config.set('opcion', 'A')
config.save()  # Persiste inmediatamente
```

### 5. Parsear con cuidado

```python
tipo, args = msg.parse_payload(mensaje)

# Verificar longitud antes de acceder
if len(args) >= 2:
    device_id = args[0]
    opcion = args[1]
else:
    # Manejar error
    pass
```

---

## Limitaciones

### RadioMessage

- Mensajes radio limitados a 64 bytes (configurable hasta 251)
- No hay confirmación automática de entrega
- Format CSV requiere set_context() antes de enviar

### ConfigManager

- Almacena solo tipos básicos: int, str, None
- No soporta listas ni diccionarios complejos
- Archivos pueden corromperse si se interrumpe escritura
- grupo inicia en 0 (ajustar a 1-9 manualmente si es necesario)

---

## Troubleshooting

### Mensajes no se reciben

**Cuándo usar**: Cuando dos dispositivos están en el mismo canal pero no se comunican. Verifica config radio y agrega logs.

```python
# Verificar configuración radio
radio.config(channel=7, power=6, length=64)
radio.on()

# Agregar logs
resultado = msg.receive(radio.receive)
if resultado:
    print("RX: {}".format(resultado['d']))
```

### Config no persiste

**Cuándo usar**: Cuando los valores vuelven a default después de reiniciar. Verifica que save() se ejecuta correctamente.

```python
# Verificar que se guarda
success = config.save()
if not success:
    print("Error guardando config")

# Verificar que se carga
success = config.load()
if not success:
    print("Config no existe, usando defaults")
```

### Comandos no reconocidos

**Cuándo usar**: Cuando el tipo de mensaje recibido no coincide con el esperado. Debug del protocolo parseando raw data.

```python
# Verificar tipo exacto
resultado = msg.receive(radio.receive)
if resultado:
    print("Tipo: '{}'".format(resultado['t']))
    print("Data: '{}'".format(resultado['d']))
```
