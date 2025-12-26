# concentrador.py

from microbit import *
import radio
from microbitcore import RadioMessage

class Concentrador:
    def __init__(self):
        # Configuracion radio
        radio.config(channel=7, power=6, length=64, queue=10)
        radio.on()
        uart.init(baudrate=115200)
        
        # Handler de mensajes
        self.msg_handler = RadioMessage(format="command")
        
        # Estado
        self.dispositivos_registrados = {}  # {(grupo, rol): device_id}
        self.polling_activo = False
        self.CONFIG_FILE = 'devices.cfg'
    
    def _to_int_if_num(self, x):
        try:
            return int(x)
        except:
            return x
    
    def extract_id_with_group(self, msg):
        t, args = self.msg_handler.parse_payload(msg)
        if t != 'ID':
            return (None, None, None)
        device_id = args[0] if len(args) >= 1 else None
        grupo = self._to_int_if_num(args[1]) if len(args) >= 2 else None
        rol = args[2] if len(args) >= 3 else None
        return (device_id, grupo, rol)
    
    def cmd_poll_group(self, grupo, rol):
        return self.msg_handler.command("POLL", grupo, rol)
    
    def extract_answer_with_group(self, msg):
        t, args = self.msg_handler.parse_payload(msg)
        if t != 'ANSWER':
            return (None, None, None, [])
        dev = None
        grp = None
        rl = None
        opciones_raw = None
        
        if len(args) >= 4:
            dev, grp, rl, opciones_raw = args[0], self._to_int_if_num(args[1]), args[2], args[3]
        elif len(args) == 3:
            grp, rl, opciones_raw = self._to_int_if_num(args[0]), args[1], args[2]
        elif len(args) == 2:
            dev, opciones_raw = args[0], args[1]
        
        opciones = []
        if opciones_raw:
            s = str(opciones_raw)
            opciones = s.split(',') if ',' in s else [s]
        return (dev, grp, rl, opciones)
    
    def enviar_usb(self, mensaje):
        print(mensaje)
        uart.write(mensaje + "\n")
    
    def cargar_dispositivos(self):
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                self.dispositivos_registrados = eval(f.read())
            self.enviar_usb('{{"type":"debug","msg":"Cargados_{}_dispositivos"}}'.format(len(self.dispositivos_registrados)))
        except:
            self.dispositivos_registrados = {}
            self.enviar_usb('{"type":"debug","msg":"Sin_dispositivos_previos"}')
    
    def guardar_dispositivos(self):
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                f.write(repr(self.dispositivos_registrados))
            self.enviar_usb('{"type":"debug","msg":"Guardado_OK"}')
        except Exception as e:
            self.enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(e)))
    
    def descubrimiento(self):
        self.enviar_usb('{"type":"debug","msg":"=== DESCUBRIMIENTO ==="}')
        display.show(Image.HEART)
        self.dispositivos_registrados.clear()
        
        self.enviar_usb('{"type":"discovery_start"}')
        
        # Broadcast REPORT
        self.msg_handler.send(radio.send, self.msg_handler.cmd_report())
        self.enviar_usb('{"type":"debug","msg":"REPORT_enviado"}')
        
        # Escuchar 10 segundos
        inicio = running_time()
        while running_time() - inicio < 10000:
            resultado = self.msg_handler.receive(radio.receive)
            if resultado and resultado['t'] == 'ID':
                device_id, grupo, rol = self.extract_id_with_group(resultado['d'])
                if device_id and grupo and rol:
                    self.procesar_id(device_id, grupo, rol)
            sleep(10)
        
        # Enviar lista completa por USB
        json_list = '{"type":"device_list","devices":['
        idx = 0
        for (g, r), did in self.dispositivos_registrados.items():
            json_list += '{{"device_id":"{}","grupo":{},"role":"{}"}}'.format(did, g, r)
            if idx < len(self.dispositivos_registrados) - 1:
                json_list += ','
            idx += 1
        json_list += ']}'
        self.enviar_usb(json_list)
        
        self.guardar_dispositivos()
        self.enviar_usb('{{"type":"discovery_end","total":{}}}'.format(len(self.dispositivos_registrados)))
        
        display.show(len(self.dispositivos_registrados))
        sleep(2000)
        display.clear()
    
    def procesar_id(self, device_id, grupo, rol):
        key = (grupo, rol)
        
        # Detectar conflicto
        if key in self.dispositivos_registrados:
            existing = self.dispositivos_registrados[key]
            self.enviar_usb('{{"type":"warning","msg":"CONFLICTO_G{}:{}_ya_existe","existing":"{}","new":"{}"}}'.format(
                grupo, rol, existing[:8], device_id[:8]
            ))
        
        # Registrar
        self.dispositivos_registrados[key] = device_id
        
        # ACK
        self.msg_handler.send(radio.send, self.msg_handler.cmd_ack(device_id))
        
        # Notificar USB
        self.enviar_usb('{{"type":"new_device","device_id":"{}","grupo":{},"role":"{}"}}'.format(
            device_id, grupo, rol
        ))
        
        display.scroll(len(self.dispositivos_registrados), delay=60)
    
    def broadcast_qparams(self, tipo, num_opciones):
        self.enviar_usb('{"type":"debug","msg":"BROADCAST_QPARAMS"}')
        
        self.msg_handler.send(radio.send, self.msg_handler.cmd_qparams(tipo, num_opciones))
        
        self.enviar_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(tipo, num_opciones))
        sleep(500)
        display.show(Image.ARROW_E)
        sleep(200)
        display.clear()
    
    def hacer_polling(self):
        self.polling_activo = True
        
        self.enviar_usb('{"type":"debug","msg":"=== POLLING ==="}')
        display.show(Image.ASLEEP)
        
        lista = list(self.dispositivos_registrados.items())
        
        for idx, ((grupo, rol), device_id) in enumerate(lista):
            display.show(str(idx + 1))
            
            respuesta = None
            intentos = 0
            
            while intentos < 2 and respuesta is None:
                # Enviar POLL:grupo:rol
                self.msg_handler.send(radio.send, self.cmd_poll_group(grupo, rol))
                
                # Esperar respuesta 200ms
                for _ in range(4):
                    resultado = self.msg_handler.receive(radio.receive)
                    if resultado and resultado['t'] == 'ANSWER':
                        _, grp, rl, opciones = self.extract_answer_with_group(resultado['d'])
                        if grp == grupo and rl == rol:
                            respuesta = opciones[0] if opciones else ""
                            break
                    sleep(50)
                
                intentos += 1
            
            if respuesta is None:
                respuesta = ""
            
            # Enviar por USB con grupo:rol
            self.enviar_usb('{{"type":"answer","device_id":"{}","grupo":{},"role":"{}","answer":"{}"}}'.format(
                device_id, grupo, rol, respuesta
            ))
        
        self.enviar_usb('{"type":"polling_complete"}')
        self.polling_activo = False
        
        display.show(Image.HAPPY)
        sleep(1000)
        display.clear()
    
    def verificar_estado(self):
        self.enviar_usb('{"type":"debug","msg":"VERIFICACION"}')
        display.show(Image.GHOST)
        
        for (grupo, rol), device_id in self.dispositivos_registrados.items():
            self.msg_handler.send(radio.send, self.msg_handler.cmd_ping(device_id))
            
            inicio = running_time()
            recibio = False
            
            while running_time() - inicio < 1000:
                resultado = self.msg_handler.receive(radio.receive)
                if resultado and resultado['t'] == 'PONG':
                    dev = self.msg_handler.extract_device_id(resultado['d'])
                    if dev == device_id:
                        recibio = True
                        break
                sleep(10)
            
            estado = "online" if recibio else "offline"
            self.enviar_usb('{{"type":"ping_result","device_id":"{}","grupo":{},"role":"{}","status":"{}"}}'.format(
                device_id, grupo, rol, estado
            ))
        
        display.clear()
    
    def procesar_comando_usb(self, linea):
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
                self.broadcast_qparams(tipo, num)
            
            elif 'start_poll' in linea:
                self.hacer_polling()
            
            elif 'start_discovery' in linea:
                self.descubrimiento()
            
            elif 'ping_all' in linea:
                self.verificar_estado()
        
        except Exception as e:
            self.enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(e)))
    
    def leer_usb(self):
        if uart.any():
            try:
                linea = uart.readline()
                if linea:
                    linea = linea.decode('utf-8').strip()
                    if linea:
                        self.procesar_comando_usb(linea)
            except:
                pass
    
    def manejar_botones(self):
        if not self.polling_activo:
            if button_a.was_pressed():
                self.descubrimiento()
            if button_b.was_pressed():
                self.verificar_estado()
    
    def run(self):
        self.enviar_usb('{"type":"debug","msg":"CONCENTRADOR_INICIADO"}')
        display.show(Image.HAPPY)
        sleep(1000)
        display.clear()
        
        self.cargar_dispositivos()
        
        while True:
            self.manejar_botones()
            self.leer_usb()
            sleep(50)

# Instanciar y ejecutar
concentrador = Concentrador()
concentrador.run()