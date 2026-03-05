# perceptron.py
from microbit import *
import music
from microbitml import Radio, ConfigManager

ACTIVITY = "pct"
PASO_A = 1   # peso del rol A
PASO_B = 2   # peso del rol B
SUMA_MAX = 22

class PerceptronApp:
    def __init__(self):
        # Roles: Z es el axon (suma), A y B son las entradas (dendritas)
        self.config = ConfigManager(roles=['Z','A','B'], grupos_max=9, grupos_min=1, extra_fields={'valor':0})
        
        cargado = self.config.load()
        print("Config_cargada:{}".format(cargado))
        print("grupo:{}".format(self.config.get('grupo')))
        print("rol:{}".format(self.config.get('role')))
        print("valor:{}".format(self.config.get('valor')))
    
        if self.config.get('valor') is None:
            self.config.set('valor', 0)
    
        grupo = self.config.get('grupo')
        rol   = self.config.get('role')
        
        # El canal de radio coincide con el numero de grupo
        self.radio = Radio(activity=ACTIVITY, channel=grupo)
        self.radio.configure(group=grupo, role=rol)
        
        # El rol Z lleva la cuenta de ambas entradas
        self.suma_total = 0
        self.valor_a = 0
        self.valor_b = 0

        self.mostrar_config()

    def mostrar_leds(self, cantidad):
        # Muestra una barra de LEDs proporcional a la cantidad (max 25)
        if cantidad == 0:
            display.clear()
            return
        cantidad = min(cantidad, 25)
        leds = ""
        for i in range(25):
            leds += "9" if i < cantidad else "0"
        patron = "{}:{}:{}:{}:{}".format(leds[0:5], leds[5:10], leds[10:15], leds[15:20], leds[20:25])
        display.show(Image(patron))

    def actualizar_valor(self, delta, peso=1):
        # No actualizar si se esta tocando pin1 (modo configuracion)
        if pin1.is_touched():
            return
        valor = self.config.get('valor')
        if valor is None:
            valor = 0
        valor = (valor + delta) % 10
        self.config.set('valor', valor)
        self.config.save()
        valor_ponderado = valor * peso
        self.mostrar_leds(valor_ponderado)
        
        # Enviar valor al rol Z del mismo grupo
        self.radio.send("VALUE", valor_ponderado)
        print("TX:{}:valor={},peso={},ponderado={}".format(self.config.get('role'), valor, peso, valor_ponderado))

    def rol_a(self):
        # Boton A baja el valor, boton B lo sube
        if button_a.was_pressed():
            self.actualizar_valor(-1, PASO_A)
        if button_b.was_pressed():
            self.actualizar_valor(1, PASO_A)

    def rol_b(self):
        if button_a.was_pressed():
            self.actualizar_valor(-1, PASO_B)
        if button_b.was_pressed():
            self.actualizar_valor(1, PASO_B)

    def rol_z(self):
        # Z escucha los valores de A y B y calcula la suma
        mensaje = self.radio.receive('VALUE')
        if mensaje.valid:
            print("RX:Z:emisor={},valores={}".format(mensaje.rol, mensaje.valores))
            try:
                valor_recibido = int(mensaje.valores[0])
                suma_anterior = self.suma_total

                # Actualizar el valor del rol que envio
                if mensaje.rol == 'A':
                    self.valor_a = valor_recibido
                elif mensaje.rol == 'B':
                    self.valor_b = valor_recibido

                self.suma_total = self.valor_a + self.valor_b
                if self.suma_total > SUMA_MAX:
                    self.suma_total = SUMA_MAX

                print("SUMA:A={},B={},total={}".format(self.valor_a, self.valor_b, self.suma_total))

                # Sonido al alcanzar el maximo (activacion del perceptron)
                if self.suma_total == SUMA_MAX and suma_anterior != SUMA_MAX:
                    music.pitch(frequency=500, duration=250, wait=False)

                self.mostrar_leds(self.suma_total)
            except Exception as error:
                print("ERR:Z:{}".format(error))

    def cambiar_config(self):
        # Mantener pin1 tocado + botones para cambiar rol y grupo
        if self.config.config_rg(pin1, button_a, button_b, self.mostrar_config):
            nuevo_grupo = self.config.get('grupo')
            self.radio.configure(group=nuevo_grupo, role=self.config.get('role'), channel=nuevo_grupo)

    def mostrar_config(self):
        rol   = self.config.get('role')
        grupo = self.config.get('grupo')
        if rol is not None:
            display.show(str(rol))
            sleep(500)
        if grupo is not None:
            display.show(str(grupo))
            sleep(500)
        display.clear()

    def step(self):
        self.cambiar_config()
        # Logo muestra la actividad actual
        if pin_logo.is_touched():
            display.show(ACTIVITY)
            sleep(500)
            self.mostrar_config()
        # Ejecutar comportamiento segun rol asignado
        if not pin1.is_touched():
            rol_actual = self.config.get('role')
            if rol_actual == 'A':
                self.rol_a()
            elif rol_actual == 'B':
                self.rol_b()
            elif rol_actual == 'Z':
                self.rol_z()

    def run(self):
        while True:
            self.step()
            sleep(50)

PerceptronApp().run()