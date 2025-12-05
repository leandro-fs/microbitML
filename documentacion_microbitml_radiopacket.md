# Documentación Técnica - MicrobitML Radio Module
**Archivo:** microbitml.py  
**Propósito:** Protocolo de comunicación radio para sistema distribuido

## Descripción General

Módulo que implementa codificación/decodificación de paquetes radio para comunicación entre micro:bits. Define un protocolo estructurado con validaciones de versión, bus y roles.

**Exports públicos:**
```python
__all__ = ["test_module_import", "RadioPacket"]
```

---

## Protocolo de Comunicación

### Formato de Paquete
```
version_token,message_bus,sender_role,payload
```

**Ejemplo:**
```
pct,3,A,6
```
- `pct`: Token de versión
- `3`: Bus de mensajes
- `A`: Rol emisor
- `6`: Datos (contador)

**Caracteres especiales:**
- Comas en payload se escapan: `,` → `_coma_`

---

## Funciones de Utilidad

### `test_module_import()`
**Propósito:** Verificar carga correcta del módulo

**Uso:**
```python
from microbitml import test_module_import
test_module_import()  # Imprime confirmación
```

**Salida:** `"microbitml module loaded successfully"`

---

## Clase Principal: RadioPacket

### `__init__()`
**Propósito:** Inicializar instancia del protocolo

**Atributos:**
```python
self.fixed_role = None  # Rol fijo opcional
```

**Uso del rol fijo:**
- Si `fixed_role` está asignado: usa ese rol al codificar
- Si es `None`: usa `current_role` global de main.py
- Permite fijar rol en instancia sin depender de global

---

### `encode(payload)`
**Propósito:** Codificar datos en formato de paquete radio

**Parámetros:**
- `payload` (cualquier tipo): Datos a transmitir (convertidos a string)

**Retorna:**
- `str`: Paquete codificado formato `version,bus,role,payload`

**Lógica:**
```python
1. Importa: version_token, message_bus, current_role desde main
2. Determina rol emisor:
   - Si fixed_role existe → usa fixed_role
   - Si no → usa current_role global
3. Construye string concatenando campos con comas
4. Escapa comas en payload: "," → "_coma_"
5. Retorna paquete completo
```

**Ejemplo:**
```python
packet = RadioPacket()
packet.fixed_role = "A"
encoded = packet.encode(42)
# Resultado: "pct,0,A,42"
```

**Escape de caracteres:**
```python
packet.encode("hello,world")
# Resultado: "pct,0,A,hello_coma_world"
```

---

### `decode(received_message, valid_origin_roles)`
**Propósito:** Decodificar y validar paquete radio recibido

**Parámetros:**
- `received_message` (str): Paquete crudo recibido
- `valid_origin_roles` (tuple/list): Roles permitidos como origen

**Retorna:**
- `tuple`: (is_valid, status_description, sender_role, decoded_payload)
  - `is_valid` (bool): True si validación exitosa
  - `status_description` (str): "OK" o mensaje de error
  - `sender_role` (str): Rol del emisor (vacío si inválido)
  - `decoded_payload` (str): Datos decodificados (vacío si inválido)

**Validaciones (en orden):**

#### 1. Validación de Versión
```python
parts[0] == version_token
```
- Si falla: error no fatal (código 9)
- Permite compatibilidad entre versiones

#### 2. Validación de Bus
```python
parts[1] == str(message_bus)
```
- Si falla: descarta mensaje silenciosamente
- Permite múltiples redes independientes

#### 3. Validación de Rol Origen
```python
parts[2] in valid_origin_roles
```
- Si falla: descarta mensaje
- Si rol == current_role: **error fatal de clonación**
  - Detección de dos dispositivos con mismo rol
  - Halt con error código 1

#### 4. Decodificación de Payload
```python
parts[3].replace("_coma_", ",")
```
- Restaura comas escapadas

**Flujo de ejecución:**
```
┌─ INICIO
│
├─ Dividir mensaje por comas → parts[]
│
├─ Validar parts[0] == version_token
│  └─ Falla: error_handler(9) + lanzar excepción
│
├─ Validar parts[1] == message_bus
│  └─ Falla: lanzar excepción
│
├─ Validar parts[2] in valid_origin_roles
│  ├─ Falla + parts[2] == current_role → HALT(1) clonación
│  └─ Falla normal → lanzar excepción
│
├─ Decodificar parts[3] → payload
│
└─ Retornar (True, "OK", rol, payload)

Excepción capturada:
└─ Retornar (False, descripción, "", "")
```

**Ejemplos de uso:**

```python
# Mensaje válido
valid, desc, role, data = packet.decode("pct,0,A,5", ("A","B"))
# Resultado: (True, "OK", "A", "5")

# Versión incorrecta
valid, desc, role, data = packet.decode("v2,0,A,5", ("A","B"))
# Resultado: (False, "parts[version_token]=v2, expected:pct", "", "")

# Bus incorrecto
valid, desc, role, data = packet.decode("pct,3,A,5", ("A","B"))
# Resultado: (False, "parts[message_bus]:3, expected:0", "", "")

# Rol no permitido
valid, desc, role, data = packet.decode("pct,0,Z,5", ("A","B"))
# Resultado: (False, "parts[originRoles]: Z not in '('A', 'B')'", "", "")

# Clonación detectada (current_role="A")
valid, desc, role, data = packet.decode("pct,0,A,5", ("A","B"))
# Resultado: HALT + error display (no retorna)
```

---

## Dependencias Circulares

### Imports dinámicos
El módulo usa imports dentro de funciones para evitar dependencias circulares:

```python
def encode(self, payload):
    from main import version_token, message_bus, current_role
    ...

def decode(self, received_message, valid_origin_roles):
    from main import version_token, message_bus, current_role, error_handler
    ...
```

**Razón:** 
- `main.py` importa `RadioPacket` de `microbitml.py`
- `microbitml.py` necesita constantes de `main.py`
- Imports locales rompen el ciclo

**Variables importadas de main.py:**
- `version_token` (str): Token de versión del protocolo
- `message_bus` (int): Bus de mensajes actual
- `current_role` (str): Rol global del nodo
- `error_handler` (func): Manejador de errores

---

## Manejo de Errores

### Error Código 9: Versión incorrecta
```python
error_handler(halt=False, error_code=9, description=...)
```
- **Severidad:** WARN
- **Acción:** Log en consola + continúa ejecución
- **Causa:** Paquete con version_token diferente

### Error Código 1: Clonación de roles
```python
error_handler(halt=True, error_code=1, description="Role cloning detected: X")
```
- **Severidad:** FATAL
- **Acción:** Loop infinito (requiere reset)
- **Causa:** Dos dispositivos con el mismo rol en mismo bus
- **Display:** Alterna entre "1" y cara triste

### Excepciones silenciosas
Validaciones de bus y rol no autorizados se manejan con `ValueError` interno:
```python
try:
    # validaciones
    raise ValueError
except Exception as e:
    print("DEBUG:RadioPacket.decode:exception=...")
    return (False, status_description, "", "")
```

---

## Casos de Uso

### Caso 1: Emisión de contador (roles A/B)
```python
# En PerceptronModel.__init__()
self.packet_output.fixed_role = role  # Fija rol "A" o "B"

# En handle_button()
encoded = self.packet_output.encode(self.counter[self.role])
radio.send(encoded)  # Envía "pct,0,A,3"
```

### Caso 2: Recepción de contador (rol Z)
```python
# En on_message_received()
valid_roles = ("A", "B")  # Z acepta de A y B
valid, desc, origin, data = packet_input.decode(message, valid_roles)

if valid:
    model.handle_message({"origin": origin, "payload": data})
```

### Caso 3: Filtrado de mensajes propios
```python
# Pre-filtro en main.py antes de decode()
parts = message.split(",")
if parts[2] == current_role:  # Emisor == receptor
    return  # Ignora (radio broadcast)
```

---

## Tabla de Validación

| Campo | Índice | Validación | Falla | Acción |
|-------|--------|------------|-------|--------|
| Version | parts[0] | == version_token | WARN | error_handler(9) |
| Bus | parts[1] | == message_bus | Silencioso | Descarta mensaje |
| Rol | parts[2] | in valid_origins | Normal | Descarta mensaje |
| Rol | parts[2] | != current_role | Fatal | HALT(1) clonación |
| Payload | parts[3] | Siempre válido | - | Unescape comas |

---

## Formato de Debugging

### Salida decode() en error:
```
DEBUG:RadioPacket.decode:exception={tipo},desc={razón},received_message='{paquete}'
```

**Ejemplo:**
```
DEBUG:RadioPacket.decode:exception=<class 'ValueError'>,desc=parts[message_bus]:3, expected:0,received_message='pct,3,A,5'
```

---

## Limitaciones y Notas

### Limitaciones
- Máximo 1 coma en payload original (más comas aumentan partes)
- No valida longitud máxima de paquete (limitado por radio.send)
- Sin checksum o CRC para detección de corrupción
- Sin ACK o retransmisión (fire-and-forget)

### Seguridad
- Clonación de roles se detecta solo si mensaje pasa otras validaciones
- Pre-filtro en `on_message_received()` evita falsos positivos
- Validación por lista blanca (`valid_origin_roles`)

### Performance
- Imports dinámicos: overhead mínimo en cada llamada
- Sin parsing complejo: solo `split()` y `replace()`
- Sin buffers: procesamiento inmediato

---

## Integración con main.py

### Inicialización
```python
# En main.py __main__
packet_input = RadioPacket()   # Para recibir
packet_output = RadioPacket()  # Para enviar

model = PerceptronModel(current_role, packet_input, packet_output)
```

### Flujo de envío
```
Botón → handle_button() → encode() → radio.send()
```

### Flujo de recepción
```
radio.receive() → on_message_received() → decode() → handle_message()
```

---

## Diagrama de Protocolo

```
EMISOR (Rol A)
    │
    ├─ Botón presionado
    ├─ counter[A] = 3
    ├─ packet.encode(3)
    │    └─ Construye: "pct,0,A,3"
    └─ radio.send("pct,0,A,3")
         │
         │  [Radio broadcast]
         │
         ↓
RECEPTOR (Rol Z)
    │
    ├─ radio.receive() → "pct,0,A,3"
    ├─ Pre-filtro: parts[2] != "Z" ✓
    ├─ packet.decode("pct,0,A,3", ("A","B"))
    │    ├─ Valida version: "pct" == "pct" ✓
    │    ├─ Valida bus: "0" == "0" ✓
    │    ├─ Valida rol: "A" in ("A","B") ✓
    │    └─ Retorna: (True, "OK", "A", "3")
    ├─ model.handle_message({"origin":"A", "payload":"3"})
    └─ counter[A] = 3 → update_output()
```

---

## Glosario

- **Bus**: Canal lógico de comunicación (0-9), permite redes separadas
- **Clonación**: Dos dispositivos con mismo rol en mismo bus (error fatal)
- **Decode**: Proceso de validar y extraer datos de paquete recibido
- **Encode**: Proceso de formatear datos en paquete de protocolo
- **Fixed role**: Rol asignado a instancia de RadioPacket (sobrescribe global)
- **Payload**: Datos útiles del mensaje (campo 4 del protocolo)
- **Valid origin roles**: Lista blanca de roles autorizados como emisores
- **Version token**: Identificador de versión del protocolo ("pct")

---

## Tabla de Referencia Rápida

| Método | Entrada | Salida | Propósito |
|--------|---------|--------|-----------|
| `__init__()` | - | RadioPacket | Crea instancia |
| `encode(payload)` | datos | string | Codifica paquete |
| `decode(msg, roles)` | string, tuple | (bool, str, str, str) | Valida y decodifica |
| `test_module_import()` | - | print | Verifica carga |

---

**Fin del documento**
