# concentrador.py
from microbit import *
from microbitml import Radio

ACTIVITY = "cqz"

class Concentrador:
    def __init__(self):
        # Canal fijo 7 para la actividad classquiz
        self.radio = Radio(activity=ACTIVITY, channel=7)
        uart.init(baudrate=115200)
        
        self.dispositivos_registrados = {}
        self.polling_activo = False
        self.ARCHIVO_CONFIG = 'devices.cfg'
    
    def enviar_usb(self, mensaje):
        uart.write(mensaje + "\n")
    
    def mostrar_config(self):
        display.show(ACTIVITY)
        sleep(500)
        display.show(len(self.dispositivos_registrados))
        sleep(500)
        display.clear()
    
    def cargar_dispositivos(self):
        # Recupera dispositivos registrados de sesiones anteriores
        try:
            with open(self.ARCHIVO_CONFIG, 'r') as archivo:
                self.dispositivos_registrados = eval(archivo.read())
            self.enviar_usb('{{"type":"debug","msg":"Cargados_{}_dispositivos"}}'.format(len(self.dispositivos_registrados)))
        except:
            self.dispositivos_registrados = {}
            self.enviar_usb('{"type":"debug","msg":"Sin_dispositivos_previos"}')
    
    def guardar_dispositivos(self):
        try:
            with open(self.ARCHIVO_CONFIG, 'w') as archivo:
                archivo.write(repr(self.dispositivos_registrados))
            self.enviar_usb('{"type":"debug","msg":"Guardado_OK"}')
        except Exception as error:
            self.enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(error)))
    
    def descubrimiento(self):
        # Fase 1: limpiar registros y pedir a todos que se identifiquen
        self.enviar_usb('{"type":"debug","msg":"=== DESCUBRIMIENTO ==="}')
        display.show(Image.HEART)
        self.dispositivos_registrados.clear()
        
        self.enviar_usb('{"type":"discovery_start"}')
        self.radio.send("REPORT")
        self.enviar_usb('{"type":"debug","msg":"REPORT_enviado"}')
        
        # Fase 2: escuchar respuestas durante 10 segundos
        inicio = running_time()
        while running_time() - inicio < 10000:
            mensaje = self.radio.receive('ID', full=True)
            if mensaje.valid:
                self.procesar_id(mensaje.devID, mensaje.grp, mensaje.rol)
            sleep(10)
        
        # Fase 3: enviar lista completa al PC
        lista_json = '{"type":"device_list","devices":['
        indice = 0
        for (grupo, rol), device_id in self.dispositivos_registrados.items():
            lista_json += '{{"activity":"{}","device_id":"{}","grupo":{},"role":"{}"}}'.format(ACTIVITY, device_id, grupo, rol)
            if indice < len(self.dispositivos_registrados) - 1:
                lista_json += ','
            indice += 1
        lista_json += ']}'
        self.enviar_usb(lista_json)
        
        self.guardar_dispositivos()
        self.enviar_usb('{{"type":"discovery_end","total":{}}}'.format(len(self.dispositivos_registrados)))
        
        display.show(len(self.dispositivos_registrados))
        sleep(2000)
        display.clear()
    
    def procesar_id(self, device_id, grupo, rol):
        clave = (grupo, rol)
        
        # Advertir si ya existe un dispositivo con ese grupo y rol
        if clave in self.dispositivos_registrados:
            existente = self.dispositivos_registrados[clave]
            self.enviar_usb('{{"type":"warning","msg":"CONFLICTO_G{}:{}","existing":"{}","new":"{}"}}'.format(
                grupo, rol, existente[:8], device_id[:8]
            ))
        
        self.dispositivos_registrados[clave] = device_id
        # Confirmar registro al dispositivo
        self.radio.send("ACK", device_id)
        
        self.enviar_usb('{{"type":"new_device","activity":"{}","device_id":"{}","grupo":{},"role":"{}"}}'.format(
            ACTIVITY, device_id, grupo, rol
        ))
        
        display.scroll(len(self.dispositivos_registrados), delay=60)
    
    def broadcast_qparams(self, tipo, num_opciones):
        # Enviar parametros de la pregunta a todos los dispositivos
        self.enviar_usb('{"type":"debug","msg":"BROADCAST_QPARAMS"}')
        self.radio.send("QPARAMS", tipo, num_opciones)
        self.enviar_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(tipo, num_opciones))
        sleep(500)
        display.show(Image.ARROW_E)
        sleep(200)
        display.clear()
    
    def hacer_polling(self):
        # Preguntar de a uno a cada dispositivo registrado su respuesta
        self.polling_activo = True
        self.enviar_usb('{"type":"debug","msg":"=== POLLING ==="}')
        display.show(Image.ASLEEP)
        
        for indice, ((grupo, rol), device_id) in enumerate(list(self.dispositivos_registrados.items())):
            display.show(str(indice + 1))
            
            respuesta = None
            intentos = 0
            
            while intentos < 2 and respuesta is None:
                self.radio.send("POLL", grupo, rol)
                
                # Esperar respuesta en ventanas de 50ms, hasta 4 intentos
                for _ in range(4):
                    mensaje = self.radio.receive('ANSWER', full=True)
                    if mensaje.valid and mensaje.grp == grupo and mensaje.rol == rol:
                        respuesta = mensaje.valores[0] if mensaje.valores else ""
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
        # Enviar PING a cada dispositivo y esperar PONG
        self.enviar_usb('{"type":"debug","msg":"VERIFICACION"}')
        display.show(Image.GHOST)
        
        for (grupo, rol), device_id in self.dispositivos_registrados.items():
            self.radio.send("PING", device_id)
            
            inicio = running_time()
            respondio = False
            
            while running_time() - inicio < 1000:
                mensaje = self.radio.receive('PONG', full=True)
                if mensaje.valid and mensaje.devID == device_id:
                    respondio = True
                    break
                sleep(10)
            
            estado = "online" if respondio else "offline"
            self.enviar_usb('{{"type":"ping_result","device_id":"{}","grupo":{},"role":"{}","status":"{}"}}'.format(
                device_id, grupo, rol, estado
            ))
        
        display.clear()
    
    def procesar_comando_usb(self, linea):
        # Interpretar comandos que llegan desde el PC por USB
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
        except Exception as error:
            self.enviar_usb('{{"type":"error","msg":"{}"}}'.format(str(error)))
    
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

    def manejar_mensajes_radio(self):
        # Escucha CHECK_REG: dispositivos que verifican si siguen registrados
        mensaje = self.radio.receive(full=True)
        
        if not mensaje.valid or not mensaje.name:
            return
        
        if mensaje.name == 'CHECK_REG':
            if not mensaje.devID or mensaje.grp is None or not mensaje.rol:
                self.enviar_usb('{"type":"warning","msg":"CHECK_REG_malformado"}')
                return
            
            self.enviar_usb('{{"type":"debug","msg":"CHECK_REG:{}:G{}:{}"}}'.format(
                mensaje.devID[:8], mensaje.grp, mensaje.rol
            ))
            
            clave = (mensaje.grp, mensaje.rol)
            if clave in self.dispositivos_registrados:
                almacenado = self.dispositivos_registrados[clave]
                if almacenado == mensaje.devID:
                    self.radio.send("REG_STATUS", mensaje.devID, "OK")
                    self.enviar_usb('{"type":"debug","msg":"REG_STATUS_OK"}')
                else:
                    # El slot esta ocupado por otro device_id
                    self.radio.send("REG_STATUS", mensaje.devID, "CONFLICT")
                    self.enviar_usb('{"type":"debug","msg":"REG_STATUS_CONFLICT"}')
            else:
                self.radio.send("REG_STATUS", mensaje.devID, "NO")
                self.enviar_usb('{"type":"debug","msg":"REG_STATUS_NO"}')
    
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
            self.manejar_mensajes_radio()
            self.leer_usb()
            sleep(50)

Concentrador().run()