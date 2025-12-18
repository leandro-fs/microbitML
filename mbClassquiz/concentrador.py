# concentrador_dual.py - OPTIMIZADO
# Reducido para memoria flash limitada
from microbit import *
import radio
import machine
from microbitcore import RadioMessage

CANALES_GRUPOS = list(range(1, 21))
CANAL_PUBLICO = 80
DISCOVERY_TIMEOUT_MS = 2000

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
lideres_por_grupo = {}
votantes_sin_lider = {}
respuestas = {}

msg_csv = RadioMessage(format="csv")
msg_cmd = RadioMessage(format="command", device_id=device_id)


def usb(t, d=""):
    uart.write("{}:{}\n".format(t, d))


def detectar_formato(m):
    return 'csv' if ',' in m and len(m.split(',')) == 4 else 'command' if ':' in m or m in ['REPORT', 'PING'] else None


def procesar_perceptron(m):
    p = m.split(',')
    if len(p) == 4:
        usb("P", "{}:{}:{}:{}".format(p[0], p[1], p[2], p[3]))


def procesar_report():
    for grupo in CANALES_GRUPOS:
        radio.config(chn=grupo)
        radio.send(msg_cmd.command("REPORT"))
        
        timeout = running_time() + DISCOVERY_TIMEOUT_MS
        lider_encontrado = False
        
        while running_time() < timeout:
            received = radio.receive()
            if received:
                decoded = msg_cmd.decode(received)
                datos = decoded.get('d')
                
                if decoded['t'] == "ID_LIDER" and datos:
                    partes = datos.split(':')
                    if len(partes) >= 2:
                        grupo_msg = int(partes[0])
                        lider_id = partes[1]
                        
                        if grupo_msg == grupo and not lider_encontrado:
                            lideres_por_grupo[grupo] = lider_id
                            lider_encontrado = True
                            radio.send(msg_cmd.command("ACK_LIDER", grupo, device_id))
                            usb("L", "{}:{}".format(grupo, lider_id[:8]))
            sleep(10)
    
    radio.config(chn=CANAL_PUBLICO)


def registrar_votantes_sin_lider():
    timeout = running_time() + 3000
    
    while running_time() < timeout:
        received = radio.receive()
        if received:
            decoded = msg_cmd.decode(received)
            datos = decoded.get('d')
            
            if decoded['t'] == "ID_VOTANTE" and datos:
                partes = datos.split(':')
                if len(partes) >= 3:
                    grupo_msg = int(partes[0])
                    rol = partes[1]
                    votante_id = partes[2]
                    
                    votantes_sin_lider[votante_id] = {'grupo': grupo_msg, 'rol': rol}
                    radio.send(msg_cmd.command("ACK_VOTANTE", votante_id, device_id))
                    usb("V", "{}:{}:{}".format(grupo_msg, rol, votante_id[:8]))
        sleep(10)


def broadcast_qparams(tipo, num):
    mensaje = msg_cmd.command("QPARAMS", tipo, num)
    
    for grupo in lideres_por_grupo.keys():
        radio.config(chn=grupo)
        radio.send(mensaje)
        sleep(50)
    
    radio.config(chn=CANAL_PUBLICO)
    radio.send(mensaje)
    sleep(50)
    
    usb("Q", "{}:{}".format(tipo, num))


def hacer_polling():
    respuestas.clear()
    
    for grupo, lider_id in lideres_por_grupo.items():
        radio.config(chn=grupo)
        radio.send(msg_cmd.cmd_poll(lider_id))
        radio.config(chn=CANAL_PUBLICO)
        
        timeout = running_time() + 2000
        respondio = False
        
        while running_time() < timeout and not respondio:
            received = radio.receive()
            if received:
                decoded = msg_cmd.decode(received)
                datos = decoded.get('d')
                
                if decoded['t'] == "ANSWER" and datos:
                    partes = datos.split(':')
                    if len(partes) >= 2:
                        respuesta_id = partes[0]
                        opcion = partes[1]
                        
                        if respuesta_id == lider_id:
                            respuestas[grupo] = opcion
                            respondio = True
                            usb("AG", "{}:{}".format(grupo, opcion))
            sleep(10)
    
    for votante_id in votantes_sin_lider.keys():
        radio.send(msg_cmd.cmd_poll(votante_id))
        
        timeout = running_time() + 1000
        respondio = False
        
        while running_time() < timeout and not respondio:
            received = radio.receive()
            if received:
                decoded = msg_cmd.decode(received)
                datos = decoded.get('d')
                
                if decoded['t'] == "ANSWER" and datos:
                    partes = datos.split(':')
                    if len(partes) >= 2:
                        respuesta_id = partes[0]
                        opcion = partes[1]
                        
                        if respuesta_id == votante_id:
                            respuestas[votante_id] = opcion
                            respondio = True
                            usb("AV", "{}:{}".format(votante_id[:8], opcion))
            sleep(10)
    
    usb("OK", str(len(respuestas)))


def procesar_comando_usb(linea):
    linea = linea.strip()
    if not linea:
        return
    
    try:
        if 'question_params' in linea:
            tipo = "unica"
            if 'multiple' in linea:
                tipo = "multiple"
            
            num = 4
            if '2' in linea:
                num = 2
            elif '3' in linea:
                num = 3
            
            broadcast_qparams(tipo, num)
        
        elif 'start_poll' in linea:
            hacer_polling()
        
        elif 'report' in linea:
            procesar_report()
        
        elif 'register' in linea:
            registrar_votantes_sin_lider()
    
    except Exception as e:
        usb("E", str(e)[:20])


def loop_principal():
    while True:
        if uart.any():
            linea = uart.readline()
            if linea:
                try:
                    procesar_comando_usb(linea.decode('utf-8'))
                except:
                    pass
        
        received = radio.receive()
        if received:
            formato = detectar_formato(received)
            
            if formato == 'csv':
                procesar_perceptron(received)
            elif formato == 'command':
                decoded = msg_cmd.decode(received)
                if decoded['t'] == "PING":
                    if msg_cmd.validate_for_me(received):
                        radio.send(msg_cmd.command("PONG", device_id, device_id))
        
        sleep(10)


uart.init(baudrate=115200)
radio.on()
radio.config(chn=CANAL_PUBLICO, power=6, length=64, queue=10)
display.show(Image.HAPPY)
sleep(1000)
display.clear()
usb("READY", device_id[:8])

loop_principal()