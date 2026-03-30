# classquiz.py
from microbit import *
from microbitml import Radio, ConfigManager

ACTIVITY = "cqz"

class ClassQuiz:
    def __init__(self):
        self.config = ConfigManager(
            roles=['A', 'B', 'C', 'D', 'E', 'Z'],
            grupos_max=9,
            grupos_min=1
        )
        self.config.load()

        self.radio = Radio(activity=ACTIVITY, channel=0)
        self.radio.configure(group=self.config.get('grupo'), role=self.config.get('role'))

        self.tipo_pregunta     = None
        self.num_opciones      = 4
        self.opcion_actual_idx = 0
        self.seleccionadas     = []
        self.registrado        = False

        self.mostrar_inicio()

    def calcular_delay_descubrimiento(self):
        grupo = self.config.get('grupo') or 1
        rol   = self.config.get('role') or 'A'
        try:
            indice_rol = self.config.roles.index(rol)
        except:
            indice_rol = 0
        slot = (grupo - 1) * len(self.config.roles) + indice_rol
        return int((slot * 5750) / 53) if slot < 54 else 0

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
        delay = self.calcular_delay_descubrimiento()
        self.log("Delay:{}ms".format(delay))
        sleep(delay)
        self.radio.send("ID", device_id=True)
        self.log("TX:ID")

    def procesar_ack(self, mensaje):
        self.registrado = True
        self.log("Registrado_OK")
        display.show(Image.DUCK)
        sleep(400)
        display.show(Image.YES)
        sleep(500)
        display.clear()

    def procesar_qparams(self, mensaje):
        # El valor llega empaquetado como un solo elemento "tipo,num_opciones"
        # Ej: valores = ['unica,4'] o valores = ['unica', '4'] segun el concentrador
        if not mensaje.valores:
            return
        if len(mensaje.valores) >= 2:
            # Formato separado: valores[0]=tipo, valores[1]=num
            tipo = mensaje.valores[0]
            num  = mensaje.valores[1]
        else:
            # Formato empaquetado: valores[0]="tipo,num"
            partes = mensaje.valores[0].split(',')
            if len(partes) < 2:
                return
            tipo = partes[0]
            num  = partes[1]

        self.tipo_pregunta     = tipo
        self.num_opciones      = int(num)
        self.opcion_actual_idx = 0
        self.seleccionadas     = [False] * self.num_opciones

        self.log("QPARAMS:{}:{}".format(self.tipo_pregunta, self.num_opciones))
        display.show(Image.ARROW_E)
        sleep(300)
        self.mostrar_estado_votacion()

    def procesar_poll(self, mensaje):
        self.log("POLL_MATCH")
        self.enviar_respuesta()

    def enviar_respuesta(self):
        letras     = ['A', 'B', 'C', 'D']
        respuestas = [letras[i] for i in range(len(self.seleccionadas)) if self.seleccionadas[i]]
        self.radio.send("ANSWER", respuestas, device_id=True, packed=True)
        self.log("TX:ANSWER:{}".format(','.join(respuestas)))
        display.show(Image.ARROW_W)
        sleep(200)
        display.clear()

    def procesar_ping(self, mensaje):
        self.log("RX:PING")
        self.radio.send("PONG", device_id=True)
        self.log("TX:PONG")

    def navegar_opcion(self):
        self.opcion_actual_idx = (self.opcion_actual_idx + 1) % self.num_opciones
        self.log('NAV:{}'.format(['A', 'B', 'C', 'D'][self.opcion_actual_idx]))
        self.mostrar_estado_votacion()

    def toggle_seleccion(self):
        indice = self.opcion_actual_idx
        self.seleccionadas[indice] = not self.seleccionadas[indice]
        if self.tipo_pregunta == "unica" and self.seleccionadas[indice]:
            for i in range(len(self.seleccionadas)):
                if i != indice:
                    self.seleccionadas[i] = False
        display.show(Image.YES if self.seleccionadas[indice] else Image.NO)
        self.log('{}:{}'.format('SELECT' if self.seleccionadas[indice] else 'DESELECT',
                                ['A', 'B', 'C', 'D'][indice]))
        sleep(400)
        self.mostrar_estado_votacion()

    def mostrar_estado_votacion(self):
        letra = ['A', 'B', 'C', 'D'][self.opcion_actual_idx]
        display.show(letra)
        if self.seleccionadas[self.opcion_actual_idx]:
            sleep(150)
            display.set_pixel(2, 2, 9)

    def manejar_mensajes_radio(self):
        mensaje = self.radio.receive()
        if not mensaje.valid:
            return

        if mensaje.name == 'REG_STATUS' and not self.registrado:
            if mensaje.valores:
                estado = mensaje.valores[0]
                self.log("REG_STATUS:{}".format(estado))
                if estado == "OK":
                    self.registrado = True
                    self.log("Registro_recuperado")
                    display.show(Image.YES)
                    sleep(800)
                    display.clear()
                elif estado == "NO":
                    self.log("No_registrado_esperar_REPORT")
                elif estado == "CONFLICT":
                    self.log("CONFLICTO_grupo_rol")
                    display.show(Image.SAD)
                    sleep(1000)
                    display.clear()
        elif mensaje.name == 'REPORT':
            self.procesar_report()
        elif mensaje.name == 'ACK':
            self.procesar_ack(mensaje)
        elif mensaje.name == 'QPARAMS':
            self.procesar_qparams(mensaje)
        elif mensaje.name == 'POLL':
            self.procesar_poll(mensaje)
        elif mensaje.name == 'PING':
            self.procesar_ping(mensaje)

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
            display.show(Image.HEART)
            sleep(100)
            display.clear()

    def cambiar_config(self):
        if self.config.config_rg(pin1, button_a, button_b, self.mostrar_config):
            self.radio.configure(group=self.config.get('grupo'), role=self.config.get('role'))

    def run(self):
        self.config.save()
        self.radio.send("CHECK_REG", device_id=True)
        self.log("CHECK_REG_enviado")
        ultimo_check = running_time()

        while True:
            if not self.registrado and running_time() - ultimo_check > 5000:
                self.radio.send("CHECK_REG", device_id=True)
                ultimo_check = running_time()
                self.log("CHECK_REG_reintento")

            self.cambiar_config()
            if pin_logo.is_touched():
                self.mostrar_config()
            self.manejar_mensajes_radio()
            self.manejar_votacion()
            sleep(20)

ClassQuiz().run()