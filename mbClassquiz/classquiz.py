# classquiz_device.py - OPTIMIZADO
from microbit import *
import radio
import machine
from random import randint
from microbitcore import RadioMessage, MultichnManager, ConfigManager

CANAL_PUBLICO = 80
LETRAS = ['A', 'B', 'C', 'D', 'E']
DELAYS = {'A': 0, 'B': 200, 'C': 400, 'D': 600, 'E': 800}

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

config = ConfigManager(
    roles=['A', 'B', 'C', 'D', 'E', 'Z'],
    grupos_max=20,
    extra_fields={'tiene_lider': False, 'voto': None, 'num_opciones': 4}
)
config.load()

msg = RadioMessage(format="command", device_id=device_id)
mcm = MultichnManager(radio)
mcm.set_chns(private=config.get('grupo'), public=CANAL_PUBLICO)

opcion_actual = 0
lider_id = None
votantes_registrados = {}
votos_recibidos = {}


def es_lider():
    return config.get('role') == 'Z'


def es_votante():
    return config.get('role') in LETRAS


def resetear_navegacion():
    global opcion_actual
    config.set('voto', None)
    opcion_actual = 0
    votos_recibidos.clear()
    display.clear()


def calcular_consenso(votos):
    if not votos:
        return ""
    conteo = {}
    for v in votos:
        if v:
            conteo[v] = conteo.get(v, 0) + 1
    if not conteo:
        return ""
    return max(conteo, key=conteo.get)


def lider_responder_report():
    mcm.send(msg.command("ID_LIDER", config.get('grupo'), device_id), "private")


def lider_escuchar_ack():
    timeout = running_time() + 2000
    while running_time() < timeout:
        received = mcm.receive("private")
        if received:
            decoded = msg.decode(received)
            if decoded['t'] == "ACK_LIDER":
                return True
        sleep(10)
    return False


def lider_registrar_votantes():
    votantes_registrados.clear()
    timeout = running_time() + 3000
    
    while running_time() < timeout:
        received = mcm.receive("private")
        if received:
            decoded = msg.decode(received)
            datos = decoded.get('d')
            if decoded['t'] == "ID_VOTANTE" and datos:
                partes = datos.split(':')
                if len(partes) >= 3:
                    grupo_msg = int(partes[0])
                    rol = partes[1]
                    votante_id = partes[2]
                    
                    if grupo_msg == config.get('grupo'):
                        votantes_registrados[votante_id] = rol
                        mcm.send(msg.command("ACK_VOTANTE", votante_id, device_id), "private")
        sleep(10)


def lider_procesar_poll():
    votos_recibidos.clear()
    timeout = running_time() + 5000
    
    while running_time() < timeout:
        received = mcm.receive("private")
        if received:
            decoded = msg.decode(received)
            datos = decoded.get('d')
            if decoded['t'] == "ANSWER" and datos:
                partes = datos.split(':')
                if len(partes) >= 2:
                    votante_id = partes[0]
                    opcion = partes[1]
                    if votante_id in votantes_registrados:
                        votos_recibidos[votante_id] = opcion
        sleep(10)
    
    votos_list = list(votos_recibidos.values())
    consenso = calcular_consenso(votos_list)
    
    if consenso:
        mcm.send(msg.command("ANSWER", device_id, consenso), "public")
        config.set('voto', consenso)


def votante_detectar_lider():
    global lider_id
    timeout = running_time() + 2500
    
    while running_time() < timeout:
        received = mcm.receive("private")
        if received:
            decoded = msg.decode(received)
            if decoded['t'] == "ACK_LIDER":
                lider_id = msg.extract_device_id(received)
                if lider_id:
                    config.set('tiene_lider', True)
                    return True
        sleep(10)
    
    config.set('tiene_lider', False)
    return False


def votante_registrar_con_lider():
    if not lider_id:
        return False
    
    delay = DELAYS.get(config.get('role'), 0)
    sleep(delay)
    
    mcm.send(msg.command("ID_VOTANTE", config.get('grupo'), config.get('role'), device_id), "private")
    
    timeout = running_time() + 3000
    while running_time() < timeout:
        received = mcm.receive("private")
        if received:
            decoded = msg.decode(received)
            datos = decoded.get('d')
            if decoded['t'] == "ACK_VOTANTE" and datos:
                partes = datos.split(':')
                if len(partes) >= 2 and partes[0] == device_id:
                    return True
        sleep(10)
    
    config.set('tiene_lider', False)
    return False


def votante_registrar_sin_lider():
    delay = DELAYS.get(config.get('role'), 0)
    sleep(delay)
    
    mcm.send(msg.command("ID_VOTANTE", config.get('grupo'), config.get('role'), device_id), "public")
    
    timeout = running_time() + 3000
    while running_time() < timeout:
        received = mcm.receive("public")
        if received:
            decoded = msg.decode(received)
            if decoded['t'] == "ACK_VOTANTE":
                return True
        sleep(10)
    return False


def votante_navegar():
    global opcion_actual
    
    if button_a.was_pressed():
        opcion_actual = (opcion_actual - 1) % config.get('num_opciones')
        display.show(LETRAS[opcion_actual])
    
    if button_b.was_pressed():
        opcion_actual = (opcion_actual + 1) % config.get('num_opciones')
        display.show(LETRAS[opcion_actual])
    
    if button_a.is_pressed() and button_b.is_pressed():
        config.set('voto', LETRAS[opcion_actual])
        if config.get('tiene_lider'):
            mcm.send(msg.cmd_vote(LETRAS[opcion_actual]), "private")
        display.show(Image.YES)
        sleep(500)
        display.clear()


def votante_responder_poll():
    voto = config.get('voto')
    if voto:
        mcm.send(msg.command("ANSWER", device_id, voto), "public")


def procesar_mensaje(received, canal):
    decoded = msg.decode(received)
    tipo = decoded['t']
    datos = decoded.get('d')
    
    if tipo == "REPORT":
        if es_lider():
            lider_responder_report()
            if lider_escuchar_ack():
                lider_registrar_votantes()
        elif es_votante():
            if votante_detectar_lider():
                votante_registrar_con_lider()
            else:
                votante_registrar_sin_lider()
    
    elif tipo == "QPARAMS" and datos:
        partes = datos.split(':')
        if len(partes) >= 2:
            config.set('num_opciones', int(partes[1]))
            resetear_navegacion()
    
    elif tipo == "VOTE" and es_lider() and datos:
        partes = datos.split(':')
        if len(partes) >= 2:
            votante_id = partes[0]
            opcion = partes[1]
            if votante_id != device_id:
                votos_recibidos[votante_id] = opcion
    
    elif tipo == "POLL":
        if es_lider() and msg.validate_for_me(received):
            lider_procesar_poll()
        elif es_votante() and not config.get('tiene_lider'):
            if msg.validate_for_me(received):
                votante_responder_poll()
    
    elif tipo == "PING":
        if msg.validate_for_me(received):
            mcm.send(msg.command("PONG", device_id, device_id), "public")


def cambiar_config():
    if pin1.is_touched():
        if button_a.was_pressed():
            config.cycle_role()
            config.save()
            display.show(str(config.get('role')))
            sleep(500)
            display.clear()
            button_a.was_pressed()
        elif button_b.was_pressed():
            config.cycle_grupo()
            config.save()
            ng = config.get('grupo')
            mcm.set_chns(private=ng, public=CANAL_PUBLICO)
            display.show(str(ng))
            sleep(500)
            display.clear()
            button_b.was_pressed()


def loop_principal():
    while True:
        cambiar_config()
        
        if not pin1.is_touched():
            if es_votante():
                votante_navegar()
            
            for canal in ["private", "public"]:
                received = mcm.receive(canal)
                if received:
                    procesar_mensaje(received, canal)
        
        sleep(50)


radio.on()
mcm.set_chns(private=config.get('grupo'), public=CANAL_PUBLICO)

r = config.get('role')
if r:
    display.show(str(r))
    sleep(300)
    display.clear()

loop_principal()