# concentrador.py - Concentrador con grupo:rol usando microbitcore

from microbit import *
import radio
from microbitcore import RadioMessage

# === CONFIGURACION ===
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()
uart.init(baudrate=115200)

msg_handler = RadioMessage(format="command")
dispositivos_registrados = {}  # {(grupo, rol): device_id}
polling_activo = False
CONFIG_FILE = 'devices.cfg'


# --- Helpers locales (microbitcore.py NO incluye variantes con grupo/rol) ---
def _to_int_if_num(x):
    try:
        return int(x)
    except:
        return x

def extract_id_with_group(msg):
    # Espera: "ID:<device_id>:<grupo>:<rol>"
    t, args = msg_handler.parse_payload(msg)
    if t != 'ID':
        return (None, None, None)
    device_id = args[0] if len(args) >= 1 else None
    grupo = _to_int_if_num(args[1]) if len(args) >= 2 else None
    rol = args[2] if len(args) >= 3 else None
    return (device_id, grupo, rol)

def cmd_poll_group(grupo, rol):
    # Se manda como comando: "POLL:<grupo>:<rol>"
    return msg_handler.command("POLL", grupo, rol)

def extract_answer_with_group(msg):
    # Soporta:
    #   "ANSWER:<dev>:<grupo>:<rol>:<opt1,opt2,...>"
    #   "ANSWER:<grupo>:<rol>:<opt1,opt2,...>" (sin dev)
    #   "ANSWER:<dev>:<opt1,opt2,...>" (legacy)
    t, args = msg_handler.parse_payload(msg)
    if t != 'ANSWER':
        return (None, None, None, [])
    dev = None
    grp = None
    rl = None
    opciones_raw = None

    if len(args) >= 4:
        dev, grp, rl, opciones_raw = args[0], _to_int_if_num(args[1]), args[2], args[3]
    elif len(args) == 3:
        grp, rl, opciones_raw = _to_int_if_num(args[0]), args[1], args[2]
    elif len(args) == 2:
        dev, opciones_raw = args[0], args[1]

    opciones = []
    if opciones_raw:
        s = str(opciones_raw)
        opciones = s.split(',') if ',' in s else [s]
    return (dev, grp, rl, opciones)


def enviar_usb(mensaje):
    """Envia JSON por USB"""
    print(mensaje)
    uart.write(mensaje + "\n")


def cargar_dispositivos():
    """Carga dispositivos desde archivo"""
    global dispositivos_registrados
    try:
        with open(CONFIG_FILE, 'r') as f:
            dispositivos_registrados = eval(f.read())
        enviar_usb('{{"type":"debug","msg":"Cargados_{}_dispositivos"}}'.format(len(dispositivos_registrados)))
    except:
        dispositivos_registrados = {}
        enviar_usb('{"type":"debug","msg":"Sin_dispositivos_previos"}')


def guardar_dispositivos():
    """Guarda dispositivos en archivo"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(dispositivos_registrados))
        enviar_usb('{"type":"debug","msg":"Guardado_OK"}')
    except Exception as e:
        enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(e)))


def descubrimiento():
    """Descubrimiento de dispositivos con grupo:rol"""
    enviar_usb('{"type":"debug","msg":"=== DESCUBRIMIENTO ==="}')
    display.show(Image.HEART)
    dispositivos_registrados.clear()
    
    enviar_usb('{"type":"discovery_start"}')
    
    # Broadcast REPORT
    msg_handler.send(radio.send, msg_handler.cmd_report())
    enviar_usb('{"type":"debug","msg":"REPORT_enviado"}')
    
    # Escuchar 10 segundos
    inicio = running_time()
    while running_time() - inicio < 10000:
        resultado = msg_handler.receive(radio.receive)
        if resultado and resultado['t'] == 'ID':
            device_id, grupo, rol = extract_id_with_group(resultado['d'])
            if device_id and grupo and rol:
                procesar_id(device_id, grupo, rol)
        sleep(10)
    
    # Enviar lista completa por USB
    json_list = '{"type":"device_list","devices":['
    idx = 0
    for (g, r), did in dispositivos_registrados.items():
        json_list += '{{"device_id":"{}","grupo":{},"role":"{}"}}'.format(did, g, r)
        if idx < len(dispositivos_registrados) - 1:
            json_list += ','
        idx += 1
    json_list += ']}'
    enviar_usb(json_list)
    
    guardar_dispositivos()
    enviar_usb('{{"type":"discovery_end","total":{}}}'.format(len(dispositivos_registrados)))
    
    display.show(len(dispositivos_registrados))
    sleep(2000)
    display.clear()


def procesar_id(device_id, grupo, rol):
    """Procesa ID con grupo:rol"""
    key = (grupo, rol)
    
    # Detectar conflicto
    if key in dispositivos_registrados:
        existing = dispositivos_registrados[key]
        enviar_usb('{{"type":"warning","msg":"CONFLICTO_G{}:{}_ya_existe","existing":"{}","new":"{}"}}'.format(
            grupo, rol, existing[:8], device_id[:8]
        ))
    
    # Registrar
    dispositivos_registrados[key] = device_id
    
    # ACK
    msg_handler.send(radio.send, msg_handler.cmd_ack(device_id))
    
    # Notificar USB
    enviar_usb('{{"type":"new_device","device_id":"{}","grupo":{},"role":"{}"}}'.format(
        device_id, grupo, rol
    ))
    
    display.scroll(len(dispositivos_registrados), delay=60)


def broadcast_qparams(tipo, num_opciones):
    """Envia parametros de pregunta"""
    enviar_usb('{"type":"debug","msg":"BROADCAST_QPARAMS"}')
    
    msg_handler.send(radio.send, msg_handler.cmd_qparams(tipo, num_opciones))
    
    enviar_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(tipo, num_opciones))
    sleep(500)
    display.show(Image.ARROW_E)
    sleep(200)
    display.clear()


def hacer_polling():
    """Polling por grupo:rol"""
    global polling_activo
    polling_activo = True
    
    enviar_usb('{"type":"debug","msg":"=== POLLING ==="}')
    display.show(Image.ASLEEP)
    
    lista = list(dispositivos_registrados.items())
    
    for idx, ((grupo, rol), device_id) in enumerate(lista):
        display.show(str(idx + 1))
        
        respuesta = None
        intentos = 0
        
        while intentos < 2 and respuesta is None:
            # Enviar POLL:grupo:rol
            msg_handler.send(radio.send, cmd_poll_group(grupo, rol))
            
            # Esperar respuesta 200ms
            for _ in range(4):
                resultado = msg_handler.receive(radio.receive)
                if resultado and resultado['t'] == 'ANSWER':
                    _, grp, rl, opciones = extract_answer_with_group(resultado['d'])
                    if grp == grupo and rl == rol:
                        respuesta = opciones[0] if opciones else ""
                        break
                sleep(50)
            
            intentos += 1
        
        if respuesta is None:
            respuesta = ""
        
        # Enviar por USB con grupo:rol
        enviar_usb('{{"type":"answer","device_id":"{}","grupo":{},"role":"{}","answer":"{}"}}'.format(
            device_id, grupo, rol, respuesta
        ))
    
    enviar_usb('{"type":"polling_complete"}')
    polling_activo = False
    
    display.show(Image.HAPPY)
    sleep(1000)
    display.clear()


def verificar_estado():
    """Verifica estado con PING"""
    enviar_usb('{"type":"debug","msg":"VERIFICACION"}')
    display.show(Image.GHOST)
    
    for (grupo, rol), device_id in dispositivos_registrados.items():
        msg_handler.send(radio.send, msg_handler.cmd_ping(device_id))
        
        inicio = running_time()
        recibio = False
        
        while running_time() - inicio < 1000:
            resultado = msg_handler.receive(radio.receive)
            if resultado and resultado['t'] == 'PONG':
                dev = msg_handler.extract_device_id(resultado['d'])
                if dev == device_id:
                    recibio = True
                    break
            sleep(10)
        
        estado = "online" if recibio else "offline"
        enviar_usb('{{"type":"ping_result","device_id":"{}","grupo":{},"role":"{}","status":"{}"}}'.format(
            device_id, grupo, rol, estado
        ))
    
    display.clear()


def procesar_comando_usb(linea):
    """Procesa comandos JSON desde USB"""
    try:
        linea = linea.strip()
        if not linea:
            return
        
        if 'question_params' in linea:
            tipo = "multiple" if 'multiple' in linea else "unica"
            num = 4
            if '2' in linea:
                num = 2
            elif '3' in linea:
                num = 3
            broadcast_qparams(tipo, num)
        
        elif 'start_poll' in linea:
            hacer_polling()
        
        elif 'start_discovery' in linea:
            descubrimiento()
        
        elif 'ping_all' in linea:
            verificar_estado()
    
    except Exception as e:
        enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(e)))


def leer_usb():
    """Lee comandos desde USB"""
    if uart.any():
        try:
            linea = uart.readline()
            if linea:
                linea = linea.decode('utf-8').strip()
                if linea:
                    procesar_comando_usb(linea)
        except:
            pass


# === INICIO ===
enviar_usb('{"type":"debug","msg":"CONCENTRADOR_INICIADO"}')
display.show(Image.HAPPY)
sleep(1000)
display.clear()

cargar_dispositivos()

# === LOOP ===
while True:
    if not polling_activo:
        if button_a.was_pressed():
            descubrimiento()
        if button_b.was_pressed():
            verificar_estado()
    
    leer_usb()
    sleep(50)
