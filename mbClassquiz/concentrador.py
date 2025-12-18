from microbit import *
import radio, machine
from microbitcore import RadioMessage

CANAL_PUBLICO = 80

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

lideres_por_grupo = {}
votantes_sin_lider = {}

msg = RadioMessage(format="command", device_id=device_id)

canal_actual = None


def switch_canal(canal):
    global canal_actual
    canal_int = int(canal)
    if canal_actual != canal_int:
        radio.config(channel=canal_int)
        canal_actual = canal_int


def enviar_json(datos):
    tipo = datos.get('type', '')
    
    if tipo == 'device_registered':
        uart.write('{{"type":"device_registered","device_id":"{}","role":"{}","group":{}}}\n'.format(
            datos.get('device_id'),
            datos.get('role'),
            datos.get('group')
        ))
    
    elif tipo == 'answer':
        uart.write('{{"type":"answer","device_id":"{}","answer":"{}","source":"{}","group":{}}}\n'.format(
            datos.get('device_id'),
            datos.get('answer'),
            datos.get('source'),
            datos.get('group')
        ))
    
    elif tipo == 'discovery_complete':
        uart.write('{{"type":"discovery_complete","lideres":{},"votantes":{}}}\n'.format(
            datos.get('lideres'),
            datos.get('votantes')
        ))
    
    elif tipo == 'error':
        uart.write('{{"type":"error","msg":"{}"}}\n'.format(datos.get('msg')))
    
    elif tipo == 'debug':
        uart.write('{{"type":"debug","msg":"{}"}}\n'.format(datos.get('msg')))


def discovery_completo():
    display.show('R')
    global lideres_por_grupo, votantes_sin_lider
    lideres_por_grupo = {}
    votantes_sin_lider = {}
    
    # Discovery por canales privados (grupos 1-20)
    for grupo in range(1, 21):
        switch_canal(grupo)
        radio.send(msg.cmd_report())
        sleep(100)
        
        tiempo_limite = running_time() + 2000
        while running_time() < tiempo_limite:
            rx = radio.receive()
            if rx:
                decoded = msg.decode(rx)
                if decoded['t'] == "ID_LIDER":
                    data = decoded.get('d')
                    if data:
                        partes = data.split(':')
                        if len(partes) >= 2 and int(partes[0]) == grupo:
                            lideres_por_grupo[grupo] = partes[1]
                            radio.send(msg.cmd_ack(partes[1]))
                            enviar_json({
                                'type': 'device_registered',
                                'device_id': partes[1],
                                'role': 'lider',
                                'group': grupo
                            })
            sleep(10)
    
    # Discovery en canal público (votantes sin líder)
    switch_canal(CANAL_PUBLICO)
    radio.send(msg.cmd_report())
    sleep(100)
    
    tiempo_limite = running_time() + 3000
    while running_time() < tiempo_limite:
        rx = radio.receive()
        if rx:
            decoded = msg.decode(rx)
            if decoded['t'] == "ID_VOTANTE":
                data = decoded.get('d')
                if data:
                    partes = data.split(':')
                    if len(partes) >= 3:
                        grupo_id = int(partes[0])
                        role = partes[1]
                        disp_id = partes[2]
                        
                        if grupo_id not in lideres_por_grupo and disp_id not in votantes_sin_lider:
                            votantes_sin_lider[disp_id] = {'role': role, 'group': grupo_id}
                            radio.send(msg.cmd_ack(disp_id))
                            enviar_json({
                                'type': 'device_registered',
                                'device_id': disp_id,
                                'role': role,
                                'group': grupo_id
                            })
        sleep(10)
    
    enviar_json({
        'type': 'discovery_complete',
        'lideres': len(lideres_por_grupo),
        'votantes': len(votantes_sin_lider)
    })
    display.clear()


def polling_respuestas():
    display.show('P')
    
    # Polling a líderes
    for grupo, lider_id in lideres_por_grupo.items():
        switch_canal(grupo)
        radio.send(msg.cmd_poll(lider_id))
        sleep(50)
        
        switch_canal(CANAL_PUBLICO)
        tiempo_limite = running_time() + 6000
        encontrado = False
        
        while running_time() < tiempo_limite and not encontrado:
            rx = radio.receive()
            if rx:
                decoded = msg.decode(rx)
                if decoded['t'] == "ANSWER":
                    disp_id, answer = msg.extract_answer(rx)
                    if disp_id == lider_id:
                        enviar_json({
                            'type': 'answer',
                            'device_id': disp_id,
                            'answer': answer[0] if answer else '',
                            'source': 'lider',
                            'group': grupo
                        })
                        encontrado = True
            sleep(10)
    
    # Polling a votantes sin líder
    for disp_id, info in votantes_sin_lider.items():
        radio.send(msg.cmd_poll(disp_id))
        sleep(50)
        
        tiempo_limite = running_time() + 3000
        encontrado = False
        
        while running_time() < tiempo_limite and not encontrado:
            rx = radio.receive()
            if rx:
                decoded = msg.decode(rx)
                if decoded['t'] == "ANSWER":
                    d_id, ans = msg.extract_answer(rx)
                    if d_id == disp_id:
                        enviar_json({
                            'type': 'answer',
                            'device_id': d_id,
                            'answer': ans[0] if ans else '',
                            'source': 'votante',
                            'group': info['group']
                        })
                        encontrado = True
            sleep(10)
    
    display.clear()


def procesar_usb(linea):
    if 'question_params' in linea:
        display.show('Q')
        
        tipo = 'unica'
        num_opciones = 4
        
        if 'multiple' in linea:
            tipo = 'multiple'
        if '2' in linea:
            num_opciones = 2
        elif '3' in linea:
            num_opciones = 3
        
        mensaje = msg.cmd_qparams(tipo, num_opciones)
        
        # Enviar a canal público
        switch_canal(CANAL_PUBLICO)
        radio.send(mensaje)
        
        # Enviar a todos los canales privados
        for grupo in range(1, 21):
            switch_canal(grupo)
            radio.send(mensaje)
        
        switch_canal(CANAL_PUBLICO)
        display.clear()
    
    elif 'start_poll' in linea:
        polling_respuestas()
    
    elif 'discovery' in linea:
        discovery_completo()
    
    elif 'list_devices' in linea:
        enviar_json({
            'type': 'debug',
            'msg': 'L:' + str(len(lideres_por_grupo)) + ' V:' + str(len(votantes_sin_lider))
        })


radio.on()
radio.config(power=6, length=64, queue=10)
uart.init(baudrate=115200)

switch_canal(CANAL_PUBLICO)

display.show('C')
sleep(800)
display.clear()

enviar_json({'type': 'debug', 'msg': 'Ready:' + device_id[:8]})

while True:
    if button_a.was_pressed():
        discovery_completo()
    
    if uart.any():
        linea = uart.readline()
        if linea:
            try:
                linea_str = linea.decode().strip()
                if linea_str:
                    procesar_usb(linea_str)
            except:
                pass
    
    sleep(50)