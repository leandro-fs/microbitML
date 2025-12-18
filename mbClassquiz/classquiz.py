from microbit import *
import radio, machine
from microbitcore import RadioMessage, ConfigManager

CANAL_PUBLICO = 80
LETRAS = ['A', 'B', 'C', 'D', 'E']
DELAYS_DISCOVERY = {'A': 0, 'B': 150, 'C': 300, 'D': 450, 'E': 600}

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

config = ConfigManager(
    roles=['A', 'B', 'C', 'D', 'E', 'Z'],
    grupos_max=20,
    extra_fields={'tiene_lider': False, 'voto': None, 'num_opciones': 4}
)
config.load()

msg = RadioMessage(format="command", device_id=device_id)

opcion_actual = 0
lider_id = None
votantes_registrados = {}
votos_recibidos_estudiantes = {}

canal_privado = config.get('grupo')
canal_actual = None


def switch_canal(publico):
    global canal_actual
    target = CANAL_PUBLICO if publico else (canal_privado or 0)
    if canal_actual != target:
        radio.config(channel=target)
        canal_actual = target


def enviar(mensaje, publico=False):
    switch_canal(publico)
    radio.send(mensaje)


def recibir(publico=False):
    switch_canal(publico)
    return radio.receive()


def calcular_consenso(votos):
    if not votos:
        return ""
    conteo = {}
    for v in votos:
        if v:
            conteo[v] = conteo.get(v, 0) + 1
    if not conteo:
        return ""
    key_max = None
    val_max = -1
    for k in conteo:
        if conteo[k] > val_max:
            val_max = conteo[k]
            key_max = k
    return key_max if key_max else ""


def resetear_voto():
    global opcion_actual
    config.set('voto', None)
    opcion_actual = 0
    votos_recibidos_estudiantes.clear()
    display.clear()


def navegacion_opciones():
    global opcion_actual
    num_opts = config.get('num_opciones') or 4
    if button_a.was_pressed():
        opcion_actual = (opcion_actual - 1) % num_opts
        display.show(LETRAS[opcion_actual])
    if button_b.was_pressed():
        opcion_actual = (opcion_actual + 1) % num_opts
        display.show(LETRAS[opcion_actual])
    if button_a.is_pressed() and button_b.is_pressed():
        config.set('voto', LETRAS[opcion_actual])
        if config.get('role') in LETRAS and config.get('tiene_lider'):
            enviar(msg.cmd_vote(LETRAS[opcion_actual]))
        display.show(Image.YES)
        sleep(500)
        display.clear()


def lider_responder_report():
    enviar(msg.command("ID_LIDER", config.get('grupo'), device_id))
    tiempo_limite = running_time() + 2000
    while running_time() < tiempo_limite:
        rx = recibir()
        if rx and msg.decode(rx)['t'] == "ACK_LIDER":
            votantes_registrados.clear()
            tiempo_registro = running_time() + 3000
            while running_time() < tiempo_registro:
                rx2 = recibir()
                if rx2:
                    decoded = msg.decode(rx2)
                    data = decoded.get('d')
                    if decoded['t'] == "ID_VOTANTE" and data:
                        partes = data.split(':')
                        if len(partes) >= 3 and int(partes[0]) == config.get('grupo'):
                            votantes_registrados[partes[2]] = partes[1]
                            enviar(msg.command("ACK_VOTANTE", partes[2], device_id))
                sleep(10)
            return True
        sleep(10)
    return False


def lider_polling():
    votos_recibidos_estudiantes.clear()
    tiempo_limite = running_time() + 5000
    while running_time() < tiempo_limite:
        rx = recibir()
        if rx:
            decoded = msg.decode(rx)
            data = decoded.get('d')
            if decoded['t'] == "ANSWER" and data:
                partes = data.split(':')
                if len(partes) >= 2 and partes[0] in votantes_registrados:
                    votos_recibidos_estudiantes[partes[0]] = partes[1]
        sleep(10)
    
    voto_lider = config.get('voto')
    if voto_lider:
        votos_recibidos_estudiantes[device_id] = voto_lider
    
    consenso = calcular_consenso(list(votos_recibidos_estudiantes.values()))
    enviar(msg.command("ANSWER", device_id, consenso), True)
    if consenso:
        config.set('voto', consenso)


def votante_descubrir_lider():
    global lider_id
    tiempo_limite = running_time() + 2500
    while running_time() < tiempo_limite:
        rx = recibir()
        if rx and msg.decode(rx)['t'] == "ACK_LIDER":
            lider_id = msg.extract_device_id(rx)
            if lider_id:
                config.set('tiene_lider', True)
                return True
        sleep(10)
    config.set('tiene_lider', False)
    return False


def votante_registrarse_lider():
    if not lider_id:
        return False
    
    role = config.get('role')
    sleep(DELAYS_DISCOVERY.get(role, 0) if role else 0)
    
    enviar(msg.command("ID_VOTANTE", config.get('grupo'), config.get('role'), device_id))
    
    tiempo_limite = running_time() + 3000
    while running_time() < tiempo_limite:
        rx = recibir()
        if rx:
            decoded = msg.decode(rx)
            data = decoded.get('d')
            if decoded['t'] == "ACK_VOTANTE" and data:
                if data.split(':')[0] == device_id:
                    return True
        sleep(10)
    
    config.set('tiene_lider', False)
    return False


def votante_registrarse_concentrador():
    role = config.get('role')
    sleep(DELAYS_DISCOVERY.get(role, 0) if role else 0)
    
    enviar(msg.command("ID_VOTANTE", config.get('grupo'), config.get('role'), device_id), True)
    
    tiempo_limite = running_time() + 3000
    while running_time() < tiempo_limite:
        rx = recibir(True)
        if rx and msg.decode(rx)['t'] == "ACK_VOTANTE":
            return True
        sleep(10)
    return False


def procesar_mensaje(rx):
    decoded = msg.decode(rx)
    tipo = decoded['t']
    data = decoded.get('d')
    
    if tipo == "REPORT":
        if config.get('role') == 'Z':
            if lider_responder_report():
                pass
        elif config.get('role') in LETRAS:
            if votante_descubrir_lider():
                votante_registrarse_lider()
            else:
                votante_registrarse_concentrador()
    
    elif tipo == "QPARAMS" and data:
        partes = data.split(':')
        if len(partes) >= 2:
            config.set('num_opciones', int(partes[1]))
            resetear_voto()
    
    elif tipo == "VOTE" and config.get('role') == 'Z' and data:
        partes = data.split(':')
        if len(partes) >= 2 and partes[0] != device_id:
            votos_recibidos_estudiantes[partes[0]] = partes[1]
    
    elif tipo == "POLL":
        if config.get('role') == 'Z' and msg.validate_for_me(rx):
            lider_polling()
        elif config.get('role') in LETRAS and not config.get('tiene_lider') and msg.validate_for_me(rx):
            voto = config.get('voto')
            if voto:
                enviar(msg.command("ANSWER", device_id, voto), True)
    
    elif tipo == "PING" and msg.validate_for_me(rx):
        enviar(msg.command("PONG", device_id, device_id), True)


radio.on()
radio.config(power=6, length=64, queue=10)
switch_canal(False)

role = config.get('role')
if role:
    display.show(str(role))
    sleep(300)
    display.clear()

while True:
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
            nuevo_grupo = config.get('grupo')
            canal_privado = nuevo_grupo
            display.show(str(nuevo_grupo))
            sleep(500)
            display.clear()
            button_b.was_pressed()
    else:
        navegacion_opciones()
        rx = recibir(False)
        if rx:
            procesar_mensaje(rx)
        rx = recibir(True)
        if rx:
            procesar_mensaje(rx)
    sleep(50)