# Documentación Técnica - MicrobitML Perceptron
**Autor:** Ramiro Alarcon Lasagno  
**Versión:** pct  
**Archivo:** main.py

## Arquitectura General

Sistema de perceptrón distribuido entre 3 micro:bits comunicados por radio:

```
Rol A (peso=1, max=3) ──┐
                        ├──> Rol Z (umbral=7) ──> output
Rol B (peso=2, max=6) ──┘
```

**Protocolo de comunicación:**
- Radio grupo 153
- Formato: `version,bus,origen,payload`
- Persistencia en archivo `config.cfg`

**Controles:**
- `Botón A/B`: Incrementar/decrementar contador
- `Pin1 + Botón A`: Cambiar rol
- `Pin1 + Botón B`: Cambiar bus (0-9)
- `Logo`: Mostrar configuración

---

## Configuración Global

### Constantes de Sistema
```python
CONFIG_FILE = 'config.cfg'       # Archivo persistencia
message_bus_max = 9              # Bus máximo (0-9)
activity = "pct"            # Actividad
```

### Pesos y Límites
```python
role_weights = {"A": 1, "B": 2}           # Multiplicadores entrada
role_counter_max = {"A": 3, "B": 6}       # Límites superiores
```

### Validación de Mensajes
```python
valid_origin_roles_per_destination = {
    "A": list(),      # A no recibe mensajes
    "B": list(),      # B no recibe mensajes
    "Z": ("A", "B")   # Z recibe de A y B
}
```

---

## Funciones de Utilidad

### `error_handler(halt=False, error_code=0, description="desc")`
**Propósito:** Manejo centralizado de errores con feedback visual

**Parámetros:**
- `halt` (bool): Si True, loop infinito (requiere reset físico)
- `error_code` (int): Código numérico mostrado en display
- `description` (str): Mensaje para consola serial

**Comportamiento:**
- Imprime: `SEVERIDAD:CODIGO:DESCRIPCION`
- Alterna display: número ↔ cara triste
- FATAL: loop infinito, WARN: continúa ejecución

---

### `load_config()`
**Propósito:** Cargar configuración persistente desde archivo

**Modifica globales:**
- `current_role`: Rol asignado
- `message_bus`: Bus de comunicación

**Lógica:**
1. Intenta abrir `config.cfg` y ejecutar `eval()`
2. Si falla: usa valores por defecto (rol A, bus 0)
3. Imprime resultado en consola

**Seguridad:** Usa `eval()` por simplicidad MicroPython (no crítico en sistema cerrado)

---

### `save_config()`
**Propósito:** Guardar configuración actual en archivo

**Guarda:**
```python
{'current_role': str, 'message_bus': int}
```

**Lógica:**
1. Serializa diccionario con `repr()`
2. Escribe en `config.cfg`
3. Si falla: log en consola, no detiene ejecución

---

### `indicator_led_on/off()`
**Propósito:** Control LED indicador en posición (4,0)

**Uso:** Señalización visual de eventos (actualmente sin uso funcional)

---

## Clase Principal: PerceptronModel

### `__init__(role, packet_input, packet_output)`
**Propósito:** Inicializar modelo según rol asignado

**Parámetros:**
- `role` (str): 'A', 'B' o 'Z'
- `packet_input` (RadioPacket): Decodificador mensajes
- `packet_output` (RadioPacket): Codificador mensajes

**Atributos creados:**
```python
self.role = role                    # Rol asignado
self.counter = {"A": 0, "B": 0}    # Contadores entrada
self.output = 0                     # Estado salida (0/1)
self.output_threshold = 7           # Umbral activación
self.packet_output.fixed_role = role  # Fija rol en paquetes
```

**Validación:** Error fatal si rol no existe

---

### `event_handler(event, param_dict)`
**Propósito:** Router de eventos a manejadores específicos

**Eventos soportados:**
- `"message"`: Mensaje radio → `handle_message()`
- `"button"`: Botón físico → `handle_button()`

**Parámetros:**
- `event` (str): Tipo de evento
- `param_dict` (dict): Parámetros contextuales

---

### `update_output()`
**Propósito:** Calcular salida del perceptrón (solo rol Z)

**Lógica:**
```
suma = counter[A] + counter[B]
if suma >= 7:
    output = 1  # beep grave 500Hz
else:
    output = 0  # beep agudo 7000Hz
```

**Visualización:**
- Centro display: suma ponderada (número)
- Columna derecha (x=4): barra vertical output (apagada/encendida)

**Audio:** Beep solo en cambios de estado

---

### `handle_message(param_dict)`
**Propósito:** Procesar mensajes radio recibidos

**Implementado para rol Z:**
```python
param_dict = {
    "origin": str,   # 'A' o 'B'
    "payload": str   # Contador como string
}
```

**Proceso:**
1. Valida origen en `counter.keys()`
2. Convierte payload a int
3. Actualiza `counter[origin]`
4. Recalcula `update_output()`

**Roles A/B:** No implementado (solo log debug)

---

### `handle_button(param_dict)`
**Propósito:** Procesar pulsaciones botones (roles A/B)

**Parámetros:**
```python
param_dict = {"button": str}  # 'a' o 'b'
```

**Lógica roles A/B:**
```
increment = 1 * role_weights[role]  # A:1, B:2

Botón A: contador += increment (respeta max)
Botón B: contador -= increment (respeta min 0)
```

**Transmisión:**
- Muestra valor en display
- Envía por radio (incluso sin cambio, para resync)

**Rol Z:** No implementado

---

## Manejadores de Eventos Físicos

### `button_a_was_pressed(config_adjust)`
**Modo config (config_adjust=True):**
- Cicla rol: A → B → Z → A
- Muestra config en display (logo touch)
- Guarda en archivo
- Log en consola

**Modo normal (config_adjust=False):**
- Delega a `model.event_handler("button", {"button": "a"})`
- Roles A/B: incrementa contador

---

### `button_b_was_pressed(config_adjust)`
**Modo config (config_adjust=True):**
- Incrementa bus: 0 → 1 → ... → 9 → 0
- Muestra config en display
- Guarda en archivo
- Log en consola

**Modo normal (config_adjust=False):**
- Delega a `model.event_handler("button", {"button": "b"})`
- Roles A/B: decrementa contador

---

### `pin_logo_is_touched()`
**Propósito:** Mostrar configuración mientras logo esté presionado

**Secuencia:**
```
[ROL 500ms] → [BUS 200ms] → loop hasta soltar
```

**Ejemplo:** A → 3 → A → 3 → ...

**Salida:** Limpia display al soltar

---

### `on_message_received(message)`
**Propósito:** Punto entrada mensajes radio

**Proceso:**
1. **Pre-filtro:** Ignora mensajes del propio rol (radio broadcast)
   ```python
   parts = message.split(",")
   if parts[2] == current_role: return
   ```

2. **Decodificación:** Usa `packet_input.decode()`
   - Valida versión, bus, origen
   
3. **Validación:** Comprueba origen en lista permitida

4. **Procesamiento:** Delega a `model.handle_message()`

**Seguridad:** Roles A/B ignoran todos los mensajes (lista vacía)

---

## Main Loop

### Secuencia de Inicio
```python
1. display.scroll(activity)  # Muestra "pct"
2. load_config()                  # Carga rol y bus
3. packet_input/output = RadioPacket()
4. radio.on() + config(group=153)
5. model = PerceptronModel(...)
6. pin_logo_is_touched()          # Muestra config inicial
7. model.update_output()          # Calcula estado inicial Z
```

### Loop Principal (Polling Continuo)
```python
while True:
    if button_a.was_pressed():
        config_adjust = pin1.is_touched()  # Detecta modo
        button_a_was_pressed(config_adjust)
    
    if button_b.was_pressed():
        config_adjust = pin1.is_touched()
        button_b_was_pressed(config_adjust)
    
    if pin_logo.is_touched():
        pin_logo_is_touched()
    
    message = radio.receive()
    if message:
        on_message_received(message)
```

**Sin delays:** Polling máxima velocidad respuesta

---

## Flujo de Datos

### Entrada (Roles A/B)
```
Botón → handle_button() → counter[self.role] → display → radio.send()
```

### Salida (Rol Z)
```
radio.receive() → on_message_received() → handle_message() 
→ counter[origen] → update_output() → display + beep
```

### Configuración (Todos)
```
Pin1 + Botón → cambio rol/bus → save_config() → archivo persistente
```

---

## Dependencias Externas

### `microbitml.RadioPacket`
**Métodos requeridos:**
- `decode(message, valid_origins)` → (bool, str, str, str)
- `encode(payload)` → str
- `fixed_role` (attr): Fija rol emisor en paquetes

**Formato esperado:** `version,bus,origen,payload`

---

## Notas Técnicas

### Limitaciones Memoria
- Sin docstrings inline
- Comentarios mínimos
- Uso de `eval()` en lugar de JSON

### Sincronización
- Roles A/B envían incluso sin cambio (resync)
- Rol Z no ACK (fire-and-forget)
- Pérdida paquetes tolerada (próxima pulsación resync)

### Seguridad
- Roles A/B no procesan mensajes entrantes
- Filtro de mensajes propios antes decodificación
- Validación origen por lista blanca

### Debugging
- Todos los `print()` van a consola serial
- Formato: `NIVEL:contexto:mensaje`
- Niveles: DEBUG, INFO, WARN, FATAL

---

## Tabla de Referencia Rápida

| Función | Rol | Entrada | Salida | Efecto |
|---------|-----|---------|--------|--------|
| `error_handler()` | Todos | código, descripción | display | Error visual |
| `load_config()` | Todos | archivo | globales | Carga persistencia |
| `save_config()` | Todos | globales | archivo | Guarda persistencia |
| `update_output()` | Z | counters A,B | display, beep | Calcula perceptrón |
| `handle_message()` | Z | radio | counter | Actualiza entrada |
| `handle_button()` | A,B | botón físico | radio | Envía contador |
| `on_message_received()` | Z | radio | modelo | Valida y procesa |

---

## Diagrama de Estados

```
INICIO
  ↓
MOSTRAR VERSION ("pct")
  ↓
CARGAR CONFIG (rol, bus)
  ↓
INICIALIZAR RADIO (grupo 153)
  ↓
CREAR MODELO
  ↓
MOSTRAR CONFIG INICIAL
  ↓
CALCULAR OUTPUT INICIAL (rol Z)
  ↓
┌─→ LOOP PRINCIPAL
│     │
│     ├─ BOTÓN A → [Pin1? Config : Normal]
│     ├─ BOTÓN B → [Pin1? Config : Normal]
│     ├─ LOGO → Mostrar config
│     └─ RADIO → Procesar mensaje
│     
└─────┘
```

---

## Glosario

- **Bus**: Canal de comunicación radio (0-9) para múltiples redes
- **Counter**: Valor actual de entrada ponderada (A:0-3, B:0-6)
- **Output**: Salida binaria del perceptrón (0/1)
- **Packet**: Mensaje codificado formato `version,bus,origen,payload`
- **Polling**: Consulta continua de eventos sin interrupciones
- **Role**: Función asignada al micro:bit (A, B o Z)
- **Threshold**: Umbral de activación (7)
- **Weight**: Peso de entrada en suma ponderada (A:1, B:2)

---

**Fin del documento**
