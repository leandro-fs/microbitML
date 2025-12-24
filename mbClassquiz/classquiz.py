# classquiz.py - classquiz con grupo:rol usando microbitcore

from microbit import *
import radio
import machine
from microbitcore import RadioMessage, ConfigManager
from random import randint

# === IDENTIFICACION ===
device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

# === CONFIGURACION RADIO ===
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# === PROTOCOLO ===
msg_handler = RadioMessage(format="command", device_id=device_id)

# === HELPERS (microbitcore no incluye group/role en comandos) ===
def calc_discovery_delay():
    g = int(config.get('grupo') or 1)
    r = str(config.get('role') or 'A')
    try:
        ridx = config.roles.index(r)
    except:
        ridx = 0
    # Grupos van de 1-9, entonces restamos 1 para el slot
    slot = (g - 1) * len(config.roles) + ridx
    # Total dispositivos: 9 grupos * 6 roles = 54
    # Delays: G1:A=0ms, G9:Z=8750ms
    max_delay = 8750
    max_slot = 53  # 0 a 53 = 54 dispositivos
    return int((slot * max_delay) / max_slot) if max_slot > 0 else 0

def cmd_id_with_group(grupo, role):
    return msg_handler.command("ID", device_id, grupo, role)

def cmd_answer_with_group(grupo, role, opcion):
    return msg_handler.command("ANSWER", device_id, grupo, role, opcion)

def log(mensaje):
    # Log por USB (serial)
    try:
        print(mensaje)
    except:
        pass

def cycle_grupo_fixed():
    """Cicla grupo entre 1-9 (no 0-9)"""
    g = config.get('grupo')
    if g is None or not isinstance(g, int):
        g = 1
    else:
        g = (g % 9) + 1 
    config.set('grupo', g)
    return g

# === CONFIGURACION GRUPO:ROL ===
config = ConfigManager(
    config_file='config.cfg',
    roles=['A', 'B', 'C', 'D', 'E', 'Z'],
    grupos_max=9
)
config.load()

# Corregir grupo=0 invalido
if config.get('grupo') == 0:
    config.set('grupo', 1)
    config.save()
    log('CFG:Corregido_grupo=0_a_grupo=1')

# === ESTADO VOTACION ===
vote_config = ConfigManager(
    config_file='vote.cfg',
    roles=[],
    extra_fields={'tipo': None, 'num_opciones': 4, 'opcion': None, 'confirmada': False}
)
vote_config.load()

# === ESTADO ===
registrado = False
modo_config = False





def mostrar_config():
    """Muestra grupo:rol en display"""
    display.show(str(config.get('role')))
    sleep(500)
    display.show(str(config.get('grupo')))
    sleep(500)
    display.clear()


def procesar_report():
    """Responde a REPORT con delay calculado"""
    log("RX:REPORT")

    # Calcular delay determinista
    delay_ms = calc_discovery_delay()
    
    # Obtener valores actuales
    grupo = config.get('grupo')
    role = config.get('role')
    
    log("CFG:G{}:{}".format(grupo, role))
    log("Delay:{}ms".format(delay_ms))
    sleep(delay_ms)

    # Enviar ID con grupo:rol
    comando = cmd_id_with_group(grupo, role)
    log("TX_CMD:{}".format(comando))
    msg_handler.send(radio.send, comando)
    log("TX:ID:G{}:{}".format(grupo, role))


def procesar_ack(mensaje):
    """Procesa ACK de registro"""
    global registrado

    if msg_handler.is_for_me(mensaje):
        registrado = True
        log("Registrado_OK")
        display.show(Image.DUCK)
        sleep(400)

        display.show(Image.YES)
        sleep(1000)
        display.clear()


def procesar_qparams(mensaje):
    """Procesa parametros de pregunta"""
    tipo, num_str = msg_handler.extract_qparams(mensaje)

    if tipo and num_str is not None:
        vote_config.set('tipo', tipo)
        vote_config.set('num_opciones', num_str)
        vote_config.set('opcion', None)
        vote_config.set('confirmada', False)
        vote_config.save()

        log("QPARAMS:{}:{}".format(tipo, num_str))

        display.show(Image.ARROW_E)
        sleep(300)
        display.clear()


def procesar_poll(mensaje):
    """Procesa POLL:grupo:rol"""
    tipo, args = msg_handler.parse_payload(mensaje)
    
    log("RX:POLL_raw:{}".format(mensaje))

    if len(args) >= 2:
        grupo_poll = int(args[0])
        rol_poll = args[1]

        mi_grupo = config.get('grupo')
        mi_rol = config.get('role')
        
        log("POLL:G{}:{}_vs_MIO:G{}:{}".format(grupo_poll, rol_poll, mi_grupo, mi_rol))

        if grupo_poll == mi_grupo and rol_poll == mi_rol:
            log("POLL_MATCH:respondiendo")
            enviar_respuesta()
        else:
            log("POLL_NO_MATCH:ignorando")


def enviar_respuesta():
    """Envia respuesta con grupo:rol"""
    opcion = vote_config.get('opcion')
    if opcion is None:
        opcion = ""

    grupo = config.get('grupo')
    role = config.get('role')

    comando = cmd_answer_with_group(grupo, role, opcion)
    log("TX_CMD:{}".format(comando))
    msg_handler.send(radio.send, comando)

    log("TX:ANSWER:G{}:{}:{}".format(grupo, role, opcion))

    display.show(Image.ARROW_W)
    sleep(200)
    display.clear()


def procesar_ping(mensaje):
    """Responde a PING"""
    if msg_handler.is_for_me(mensaje):
        log("RX:PING")
        msg_handler.send(radio.send, msg_handler.cmd_pong())
        log("TX:PONG")


def navegar_opcion(direccion):
    """Navega entre opciones A,B,C,D"""
    if vote_config.get('confirmada'):
        return

    opcion_actual = vote_config.get('opcion')
    num_opciones = vote_config.get('num_opciones')

    opciones = ['A', 'B', 'C', 'D'][:num_opciones]

    if opcion_actual is None:
        idx = 0
    else:
        try:
            idx = opciones.index(opcion_actual)
        except:
            idx = 0

    if direccion == 1:
        idx = (idx + 1) % len(opciones)
    else:
        idx = (idx - 1) % len(opciones)

    vote_config.set('opcion', opciones[idx])
    vote_config.save()

    display.show(opciones[idx])
    sleep(300)
    display.clear()


def confirmar_voto():
    """Confirma el voto actual"""
    if vote_config.get('opcion') is not None:
        vote_config.set('confirmada', True)
        vote_config.save()

        display.show(Image.YES)
        sleep(500)
        display.clear()


def resetear_voto():
    """Resetea el voto"""
    vote_config.set('opcion', None)
    vote_config.set('confirmada', False)
    vote_config.save()

    display.show(Image.NO)
    sleep(300)
    display.clear()


# === INICIO ===
display.show(Image.HEART)
sleep(500)
display.clear()

# === LOOP PRINCIPAL ===
while True:
    # === MODO CONFIGURACION ===
    if pin1.is_touched():
        modo_config = True

        log('CFG:PIN1_inicio')
        
        sleep(200)  # Debounce inicial
        
        # Mientras pin1 está tocado, esperar botones
        while pin1.is_touched():
            # Cambiar rol con A
            if button_a.was_pressed():
                log('BTN:A (cfg)')
                config.cycle_role()
                config.save()
                display.clear()
                sleep(100)
                mostrar_config()

                
                # Esperar a que suelte A
                while button_a.is_pressed():
                    sleep(50)
            
            # Cambiar grupo con B
            if button_b.was_pressed():
                log('BTN:B (cfg)')
                cycle_grupo_fixed()
                config.save()
                display.clear()
                sleep(100)
                mostrar_config()
                
                # Esperar a que suelte B
                while button_b.is_pressed():
                    sleep(50)
            
            sleep(50)
        
        # Al soltar pin1, salir
        display.clear()
        log('CFG:PIN1_fin')
        modo_config = False
        sleep(200)  # Debounce final

    # === LOGO: MOSTRAR GRUPO:ROL ===
    if pin_logo.is_touched():
        log('BTN:LOGO')
        mostrar_config()

    # === MENSAJES RADIO ===
    resultado = msg_handler.receive(radio.receive)
    if resultado:
        tipo = resultado['t']
        data = resultado['d']

        if tipo == 'REPORT':
            procesar_report()

        elif tipo == 'ACK':
            procesar_ack(data)

        elif tipo == 'QPARAMS':
            procesar_qparams(data)

        elif tipo == 'POLL':
            procesar_poll(data)

        elif tipo == 'PING':
            procesar_ping(data)

    # === VOTACION (solo si registrado) ===
    if registrado:
        # Boton A: navegar opciones
        if button_a.was_pressed():
            log('BTN:A')
            navegar_opcion(1)

        # Boton B: navegar opciones (reversa)
        if button_b.was_pressed():
            log('BTN:B')
            navegar_opcion(-1)

        # A+B: confirmar
        if button_a.is_pressed() and button_b.is_pressed():
            log('BTN:A+B')
            confirmar_voto()
            sleep(500)

    # === BOTONES CUANDO NO REGISTRADO ===
    else:
        a = button_a.was_pressed()
        b = button_b.was_pressed()
        if a or b:
            log('BTN:' + ('A' if a else '') + ('B' if b else ''))
            mostrar_config()

    sleep(20)