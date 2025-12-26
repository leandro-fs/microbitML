# classquiz.py

from microbit import *
import radio
import machine
from microbitcore import RadioMessage, ConfigManager
from random import randint

class ClassQuiz:
    def __init__(self):
        # Identificacion
        self.device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
        
        # Configuracion radio
        radio.config(channel=7, power=6, length=64, queue=10)
        radio.on()
        
        # Protocolo
        self.msg_handler = RadioMessage(format="command", device_id=self.device_id)
        
        # Configuracion grupo:rol
        self.config = ConfigManager(
            config_file='config.cfg',
            roles=['A', 'B', 'C', 'D', 'E', 'Z'],
            grupos_max=9
        )
        self.config.load()
        
        # Corregir grupo=0 invalido
        if self.config.get('grupo') == 0:
            self.config.set('grupo', 1)
            self.config.save()
            self.log('CFG:Corregido_grupo=0_a_grupo=1')
        
        # Estado votacion NUEVO
        self.tipo_pregunta = None  # "unica" o "multiple"
        self.num_opciones = 4
        self.opcion_actual_idx = 0  # Cursor navegacion
        self.seleccionadas = []  # [False, False, False, False]
        
        # Estado
        self.registrado = False
        self.modo_config = False
    
    def calc_discovery_delay(self):
        g = int(self.config.get('grupo') or 1)
        r = str(self.config.get('role') or 'A')
        try:
            ridx = self.config.roles.index(r)
        except:
            ridx = 0
        slot = (g - 1) * len(self.config.roles) + ridx
        max_delay = 8750
        max_slot = 53
        return int((slot * max_delay) / max_slot) if max_slot > 0 else 0
    
    def cmd_id_with_group(self, grupo, role):
        return self.msg_handler.command("ID", self.device_id, grupo, role)
    
    def cmd_answer_with_group(self, grupo, role, respuesta):
        return self.msg_handler.command("ANSWER", self.device_id, grupo, role, respuesta)
    
    def log(self, mensaje):
        try:
            print(mensaje)
        except:
            pass
    
    def cycle_grupo_fixed(self):
        g = self.config.get('grupo')
        if g is None or not isinstance(g, int):
            g = 1
        else:
            g = (g % 9) + 1
        self.config.set('grupo', g)
        return g
    
    def mostrar_config(self):
        display.show(str(self.config.get('role')))
        sleep(500)
        display.show(str(self.config.get('grupo')))
        sleep(500)
        display.clear()
    
    def procesar_report(self):
        self.log("RX:REPORT")
        delay_ms = self.calc_discovery_delay()
        grupo = self.config.get('grupo')
        role = self.config.get('role')
        self.log("CFG:G{}:{}".format(grupo, role))
        self.log("Delay:{}ms".format(delay_ms))
        sleep(delay_ms)
        comando = self.cmd_id_with_group(grupo, role)
        self.log("TX_CMD:{}".format(comando))
        self.msg_handler.send(radio.send, comando)
        self.log("TX:ID:G{}:{}".format(grupo, role))
    
    def procesar_ack(self, mensaje):
        if self.msg_handler.is_for_me(mensaje):
            self.registrado = True
            self.log("Registrado_OK")
            display.show(Image.DUCK)
            sleep(400)
            display.show(Image.YES)
            sleep(1000)
            display.clear()
    
    def procesar_qparams(self, mensaje):
        tipo, num_str = self.msg_handler.extract_qparams(mensaje)
        if tipo and num_str is not None:
            self.tipo_pregunta = tipo
            self.num_opciones = num_str
            
            # Reiniciar estado votacion
            self.opcion_actual_idx = 0
            self.seleccionadas = [False] * self.num_opciones
            
            self.log("QPARAMS:{}:{}".format(tipo, num_str))
            display.show(Image.ARROW_E)
            sleep(300)
            
            # Mostrar opcion inicial
            self.mostrar_estado_votacion()
    
    def procesar_poll(self, mensaje):
        tipo, args = self.msg_handler.parse_payload(mensaje)
        self.log("RX:POLL_raw:{}".format(mensaje))
        if len(args) >= 2:
            grupo_poll = int(args[0])
            rol_poll = args[1]
            mi_grupo = self.config.get('grupo')
            mi_rol = self.config.get('role')
            self.log("POLL:G{}:{}_vs_MIO:G{}:{}".format(grupo_poll, rol_poll, mi_grupo, mi_rol))
            if grupo_poll == mi_grupo and rol_poll == mi_rol:
                self.log("POLL_MATCH:respondiendo")
                self.enviar_respuesta()
            else:
                self.log("POLL_NO_MATCH:ignorando")
    
    def enviar_respuesta(self):
        # Generar string respuesta
        opciones_letras = ['A', 'B', 'C', 'D']
        respuestas = []
        
        for i in range(len(self.seleccionadas)):
            if self.seleccionadas[i]:
                respuestas.append(opciones_letras[i])
        
        respuesta_str = ','.join(respuestas) if respuestas else ""
        
        grupo = self.config.get('grupo')
        role = self.config.get('role')
        comando = self.cmd_answer_with_group(grupo, role, respuesta_str)
        self.log("TX_CMD:{}".format(comando))
        self.msg_handler.send(radio.send, comando)
        self.log("TX:ANSWER:G{}:{}:{}".format(grupo, role, respuesta_str))
        display.show(Image.ARROW_W)
        sleep(200)
        display.clear()
    
    def procesar_ping(self, mensaje):
        if self.msg_handler.is_for_me(mensaje):
            self.log("RX:PING")
            self.msg_handler.send(radio.send, self.msg_handler.cmd_pong())
            self.log("TX:PONG")
    
    def navegar_opcion(self):
        """Boton A: Avanza cursor"""
        self.opcion_actual_idx = (self.opcion_actual_idx + 1) % self.num_opciones
        self.log('NAV:{}'.format(['A','B','C','D'][self.opcion_actual_idx]))
        self.mostrar_estado_votacion()
    
    def toggle_seleccion(self):
        """Boton B: Toggle seleccion en cursor actual"""
        idx = self.opcion_actual_idx
        
        # Toggle
        self.seleccionadas[idx] = not self.seleccionadas[idx]
        
        # Si es "unica" y acabamos de seleccionar, deseleccionar resto
        if self.tipo_pregunta == "unica" and self.seleccionadas[idx]:
            for i in range(len(self.seleccionadas)):
                if i != idx:
                    self.seleccionadas[i] = False
        
        # Feedback visual
        if self.seleccionadas[idx]:
            display.show(Image.YES)
            self.log('SELECT:{}'.format(['A','B','C','D'][idx]))
        else:
            display.show(Image.NO)
            self.log('DESELECT:{}'.format(['A','B','C','D'][idx]))
        
        sleep(400)
        self.mostrar_estado_votacion()
    
    def mostrar_estado_votacion(self):
        """Muestra letra actual, con indicator si esta seleccionada"""
        letra = ['A', 'B', 'C', 'D'][self.opcion_actual_idx]
        
        # Mostrar letra base
        display.show(letra)
        
        # Si esta seleccionada, parpadear pixel central
        if self.seleccionadas[self.opcion_actual_idx]:
            sleep(150)
            display.set_pixel(2, 2, 9)
    
    def manejar_modo_config(self):
        if pin1.is_touched():
            self.modo_config = True
            self.log('CFG:PIN1_inicio')
            sleep(200)
            
            while pin1.is_touched():
                if button_a.was_pressed():
                    self.log('BTN:A (cfg)')
                    self.config.cycle_role()
                    self.config.save()
                    display.clear()
                    sleep(100)
                    self.mostrar_config()
                    while button_a.is_pressed():
                        sleep(50)
                
                if button_b.was_pressed():
                    self.log('BTN:B (cfg)')
                    self.cycle_grupo_fixed()
                    self.config.save()
                    display.clear()
                    sleep(100)
                    self.mostrar_config()
                    while button_b.is_pressed():
                        sleep(50)
                
                sleep(50)
            
            display.clear()
            self.log('CFG:PIN1_fin')
            self.modo_config = False
            sleep(200)
    
    def manejar_logo(self):
        if pin_logo.is_touched():
            self.log('BTN:LOGO')
            self.mostrar_config()
    
    def manejar_mensajes_radio(self):
        resultado = self.msg_handler.receive(radio.receive)
        if resultado:
            tipo = resultado['t']
            data = resultado['d']
            
            if tipo == 'REPORT':
                self.procesar_report()
            elif tipo == 'ACK':
                self.procesar_ack(data)
            elif tipo == 'QPARAMS':
                self.procesar_qparams(data)
            elif tipo == 'POLL':
                self.procesar_poll(data)
            elif tipo == 'PING':
                self.procesar_ping(data)
    
    def manejar_votacion(self):
        if self.registrado and self.tipo_pregunta is not None:
            # Boton A: Navegar
            if button_a.was_pressed():
                self.log('BTN:A')
                self.navegar_opcion()
                while button_a.is_pressed():
                    sleep(50)
            
            # Boton B: Toggle seleccion
            if button_b.was_pressed():
                self.log('BTN:B')
                self.toggle_seleccion()
                while button_b.is_pressed():
                    sleep(50)
        
        elif self.registrado:
            # Sin pregunta activa, mostrar config
            if button_a.was_pressed() or button_b.was_pressed():
                self.mostrar_config()
        
        else:
            # No registrado
            if button_a.was_pressed() or button_b.was_pressed():
                self.log('BTN:No_registrado')
                self.mostrar_config()
    
    def run(self):
        display.show(Image.HEART)
        sleep(500)
        display.clear()
        
        while True:
            self.manejar_modo_config()
            self.manejar_logo()
            self.manejar_mensajes_radio()
            self.manejar_votacion()
            sleep(20)

# Instanciar y ejecutar
app = ClassQuiz()
app.run()