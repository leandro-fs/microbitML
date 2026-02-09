# classquiz.py
from microbit import *
from microbitml import RadioMessage, ConfigManager
from random import randint

ACTIVITY = "cqz"

class ClassQuiz:
    def __init__(self):
        self.config = ConfigManager(
            roles=['A', 'B', 'C', 'D', 'E', 'Z'],
            grupos_max=9,
            grupos_min=1
        )
        self.config.load()
        
        g = self.config.get('grupo')
        self.msg = RadioMessage(activity=ACTIVITY, channel=7)
        self.msg.configure(group=g, role=self.config.get('role'))
        
        # Estado votacion
        self.tipo_pregunta = None
        self.num_opciones = 4
        self.opcion_actual_idx = 0
        self.seleccionadas = []
        self.registrado = False
        
        self.mostrar_inicio()
    
    def calc_discovery_delay(self):
        g = self.config.get('grupo') or 1
        r = self.config.get('role') or 'A'
        try:
            ridx = self.config.roles.index(r)
        except:
            ridx = 0
        slot = (g - 1) * len(self.config.roles) + ridx
        return int((slot * 8750) / 53) if slot < 54 else 0
    
    def log(self, mensaje):
        try:
            print(mensaje)
        except:
            pass
    
    def mostrar_inicio(self):
        display.show(Image.HEART)
        sleep(500)
        display.clear()
    
    def mostrar_config(self):
        display.show(str(self.config.get('role')))
        sleep(500)
        display.show(str(self.config.get('grupo')))
        sleep(500)
        display.clear()
    
    def procesar_report(self):
        self.log("RX:REPORT")
        delay_ms = self.calc_discovery_delay()
        self.log("Delay:{}ms".format(delay_ms))
        sleep(delay_ms)
        
        self.msg.send(self.msg.cmd("ID", ACTIVITY, device_id=True, gr=True))
        self.log("TX:ID")
    
    def procesar_ack(self, mensaje):
        if self.msg.is_for_me(mensaje):
            self.registrado = True
            self.log("Registrado_OK")
            display.show(Image.DUCK)
            sleep(400)
            display.show(Image.YES)
            sleep(1000)
            display.clear()
    
    def procesar_qparams(self, mensaje):
        tipo, num = self.msg.extract_qparams(mensaje)
        if tipo and num is not None:
            self.tipo_pregunta = tipo
            self.num_opciones = num
            self.opcion_actual_idx = 0
            self.seleccionadas = [False] * num
            
            self.log("QPARAMS:{}:{}".format(tipo, num))
            display.show(Image.ARROW_E)
            sleep(300)
            self.mostrar_estado_votacion()
    
    def procesar_poll(self, mensaje):
        tipo, args = self.msg.parse_payload(mensaje)
        if len(args) >= 2:
            grupo_poll = int(args[0])
            rol_poll = args[1]
            mi_grupo = self.config.get('grupo')
            mi_rol = self.config.get('role')
            
            if grupo_poll == mi_grupo and rol_poll == mi_rol:
                self.log("POLL_MATCH")
                self.enviar_respuesta()
    
    def enviar_respuesta(self):
        opciones_letras = ['A', 'B', 'C', 'D']
        respuestas = [opciones_letras[i] for i in range(len(self.seleccionadas)) if self.seleccionadas[i]]
        
        self.msg.send(self.msg.cmd("ANSWER", respuestas, device_id=True, gr=True, packed=True))
        self.log("TX:ANSWER:{}".format(','.join(respuestas)))
        display.show(Image.ARROW_W)
        sleep(200)
        display.clear()
    
    def procesar_ping(self, mensaje):
        if self.msg.is_for_me(mensaje):
            self.log("RX:PING")
            self.msg.send(self.msg.cmd("PONG", device_id=True))
            self.log("TX:PONG")
    
    def navegar_opcion(self):
        self.opcion_actual_idx = (self.opcion_actual_idx + 1) % self.num_opciones
        self.log('NAV:{}'.format(['A', 'B', 'C', 'D'][self.opcion_actual_idx]))
        self.mostrar_estado_votacion()
    
    def toggle_seleccion(self):
        idx = self.opcion_actual_idx
        self.seleccionadas[idx] = not self.seleccionadas[idx]
        
        if self.tipo_pregunta == "unica" and self.seleccionadas[idx]:
            for i in range(len(self.seleccionadas)):
                if i != idx:
                    self.seleccionadas[i] = False
        
        display.show(Image.YES if self.seleccionadas[idx] else Image.NO)
        self.log('{}:{}'.format('SELECT' if self.seleccionadas[idx] else 'DESELECT', ['A', 'B', 'C', 'D'][idx]))
        sleep(400)
        self.mostrar_estado_votacion()
    
    def mostrar_estado_votacion(self):
        letra = ['A', 'B', 'C', 'D'][self.opcion_actual_idx]
        display.show(letra)
        if self.seleccionadas[self.opcion_actual_idx]:
            sleep(150)
            display.set_pixel(2, 2, 9)
    
    def manejar_mensajes_radio(self):
        valid, tipo, payload = self.msg.recibe()
        if valid:
            if tipo == 'REPORT':
                self.procesar_report()
            elif tipo == 'ACK':
                self.procesar_ack(payload)
            elif tipo == 'QPARAMS':
                self.procesar_qparams(payload)
            elif tipo == 'POLL':
                self.procesar_poll(payload)
            elif tipo == 'PING':
                self.procesar_ping(payload)
    
    def manejar_votacion(self):
        if self.registrado and self.tipo_pregunta is not None:
            if button_a.was_pressed():
                self.log('BTN:A')
                self.navegar_opcion()
                while button_a.is_pressed():
                    sleep(50)
            
            if button_b.was_pressed():
                self.log('BTN:B')
                self.toggle_seleccion()
                while button_b.is_pressed():
                    sleep(50)
        elif self.registrado or button_a.was_pressed() or button_b.was_pressed():
            self.mostrar_config()
    
    def cambiar_config(self):
        if self.config.config_rg(pin1, button_a, button_b, self.mostrar_config):
            ng = self.config.get('grupo')
            self.msg.configure(group=ng, role=self.config.get('role'))
    
    def run(self):
        while True:
            self.cambiar_config()
            if pin_logo.is_touched():
                display.show(ACTIVITY)
                sleep(500)
                self.mostrar_config()
            self.manejar_mensajes_radio()
            self.manejar_votacion()
            sleep(20)

ClassQuiz().run()