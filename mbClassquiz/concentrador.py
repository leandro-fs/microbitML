# concentrador.py
from microbit import *
from microbitml import RadioMessage

ACTIVITY = "cqz"

class Concentrador:
    def __init__(self):
        self.msg = RadioMessage(activity=ACTIVITY, channel=7)
        uart.init(baudrate=115200)
        
        self.dispositivos_registrados = {}
        self.polling_activo = False
        self.CONFIG_FILE = 'devices.cfg'
    
    def enviar_usb(self, mensaje):
        uart.write(mensaje + "\n")
    
    def mostrar_config(self):
        display.show(ACTIVITY)
        sleep(500)
        display.show(len(self.dispositivos_registrados))
        sleep(500)
        display.clear()
    
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
        self.msg.send(self.msg.cmd("REPORT"))
        self.enviar_usb('{"type":"debug","msg":"REPORT_enviado"}')
        
        inicio = running_time()
        while running_time() - inicio < 10000:
            valid, tipo, dev, grp, rol, valores = self.msg.recibe('ID', unpack=True)
            if valid and len(valores) > 0 and valores[0] == ACTIVITY:
                self.procesar_id(dev, grp, rol)
            sleep(10)
        
        # Enviar lista completa
        json_list = '{"type":"device_list","devices":['
        idx = 0
        for (g, r), did in self.dispositivos_registrados.items():
            json_list += '{{"activity":"{}","device_id":"{}","grupo":{},"role":"{}"}}'.format(ACTIVITY, did, g, r)
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
        
        if key in self.dispositivos_registrados:
            existing = self.dispositivos_registrados[key]
            self.enviar_usb('{{"type":"warning","msg":"CONFLICTO_G{}:{}","existing":"{}","new":"{}"}}'.format(
                grupo, rol, existing[:8], device_id[:8]
            ))
        
        self.dispositivos_registrados[key] = device_id
        self.msg.send(self.msg.cmd("ACK", device_id))
        
        self.enviar_usb('{{"type":"new_device","activity":"{}","device_id":"{}","grupo":{},"role":"{}"}}'.format(
            ACTIVITY, device_id, grupo, rol
        ))
        
        display.scroll(len(self.dispositivos_registrados), delay=60)
    
    def broadcast_qparams(self, tipo, num_opciones):
        self.enviar_usb('{"type":"debug","msg":"BROADCAST_QPARAMS"}')
        self.msg.send(self.msg.cmd("QPARAMS", tipo, num_opciones))
        self.enviar_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(tipo, num_opciones))
        sleep(500)
        display.show(Image.ARROW_E)
        sleep(200)
        display.clear()
    
    def hacer_polling(self):
        self.polling_activo = True
        self.enviar_usb('{"type":"debug","msg":"=== POLLING ==="}')
        display.show(Image.ASLEEP)
        
        for idx, ((grupo, rol), device_id) in enumerate(list(self.dispositivos_registrados.items())):
            display.show(str(idx + 1))
            
            respuesta = None
            intentos = 0
            
            while intentos < 2 and respuesta is None:
                self.msg.send(self.msg.cmd("POLL", grupo, rol))
                
                for _ in range(4):
                    valid, tipo, dev, grp, rl, valores = self.msg.recibe('ANSWER', unpack=True)
                    if valid and grp == grupo and rl == rol:
                        respuesta = valores[0] if valores else ""
                        break
                    sleep(50)
                
                intentos += 1
            
            if respuesta is None:
                respuesta = ""
            
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
            self.msg.send(self.msg.cmd("PING", device_id))
            
            inicio = running_time()
            recibio = False
            
            while running_time() - inicio < 1000:
                valid, tipo, payload = self.msg.recibe('PONG')
                if valid and self.msg.extract_device_id(payload) == device_id:
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
            if pin_logo.is_touched():
                self.mostrar_config()
            self.leer_usb()
            sleep(50)

Concentrador().run()