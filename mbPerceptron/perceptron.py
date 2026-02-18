# perceptron.py
from microbit import *
import music
from microbitml import RadioMessage, ConfigManager

ACTIVITY = "pct"
STEP_A = 1
STEP_B = 2
SUMA_MAX = 22

class PerceptronApp:
    def __init__(self):
        self.config = ConfigManager(roles=['Z','A','B'], grupos_max=9, grupos_min=0, extra_fields={'valor':0})
        
        loaded = self.config.load()
        print("Config_loaded:{}".format(loaded))
        print("grupo:{}".format(self.config.get('grupo')))
        print("role:{}".format(self.config.get('role')))
        print("valor:{}".format(self.config.get('valor')))
    
        if self.config.get('valor') is None:
            self.config.set('valor', 0)
    
        g = self.config.get('grupo')
        r = self.config.get('role')
        
        self.msg = RadioMessage(activity=ACTIVITY, channel=g)
        self.msg.configure(group=g, role=r)
        
        self.suma_total = 0
        self.valor_a = 0
        self.valor_b = 0

        self.mostrar_config()

    def mostrar_leds(self, n):
        if n == 0:
            display.clear()
            return
        n = min(n, 25)
        leds = ""
        for i in range(25):
            leds += "9" if i < n else "0"
        patron = "{}:{}:{}:{}:{}".format(leds[0:5], leds[5:10], leds[10:15], leds[15:20], leds[20:25])
        display.show(Image(patron))

    def actualizar_valor(self, delta, peso=1):
        if pin1.is_touched():
            return
        v = self.config.get('valor')
        if v is None:
            v = 0
        v = (v + delta) % 10
        self.config.set('valor', v)
        self.config.save()
        vp = v * peso
        self.mostrar_leds(vp)
        
        self.msg.send(self.msg.cmd("VALUE", vp, gr=True))
        print("TX:{}:v={},peso={},vp={}".format(self.config.get('role'), v, peso, vp))

    def rol_a(self):
        if button_a.was_pressed():
            self.actualizar_valor(-1, STEP_A)
        if button_b.was_pressed():
            self.actualizar_valor(1, STEP_A)

    def rol_b(self):
        if button_a.was_pressed():
            self.actualizar_valor(-1, STEP_B)
        if button_b.was_pressed():
            self.actualizar_valor(1, STEP_B)

    def rol_z(self):
        valid, tipo, payload = self.msg.receive('VALUE')
        if valid:
            _, args = self.msg.parse_payload(payload)
            if len(args) >= 3:
                grupo, rol, valor_str = args[0], args[1], args[2]
                
                print("RX:Z:sender={},payload={}".format(rol, valor_str))
                try:
                    val = int(valor_str)
                    suma_anterior = self.suma_total

                    if rol == 'A':
                        self.valor_a = val
                    elif rol == 'B':
                        self.valor_b = val

                    self.suma_total = self.valor_a + self.valor_b
                    if self.suma_total > SUMA_MAX:
                        self.suma_total = SUMA_MAX

                    print("SUMA:A={},B={},total={}".format(self.valor_a, self.valor_b, self.suma_total))

                    if self.suma_total == SUMA_MAX and suma_anterior != SUMA_MAX:
                        music.pitch(frequency=500, duration=250, wait=False)

                    self.mostrar_leds(self.suma_total)
                except Exception as e:
                    print("ERR:Z:{}".format(e))

    def cambiar_config(self):
        if self.config.config_rg(pin1, button_a, button_b, self.mostrar_config):
            ng = self.config.get('grupo')
            self.msg.configure(group=ng, role=self.config.get('role'), channel=ng)

    def mostrar_config(self):
        r = self.config.get('role')
        g = self.config.get('grupo')
        if r is not None:
            display.show(str(r))
            sleep(500)
        if g is not None:
            display.show(str(g))
            sleep(500)
        display.clear()

    def step(self):
        self.cambiar_config()
        if pin_logo.is_touched():
            display.show(ACTIVITY)
            sleep(500)
            self.mostrar_config()
        if not pin1.is_touched():
            ra = self.config.get('role')
            if ra == 'A':
                self.rol_a()
            elif ra == 'B':
                self.rol_b()
            elif ra == 'Z':
                self.rol_z()

    def run(self):
        while True:
            self.step()
            sleep(50)

PerceptronApp().run()