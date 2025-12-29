# perceptron.py
from microbit import *
import radio
import music
import machine
from microbitcore import RadioMessage, ConfigManager

ACTIVITY = "pct"
SUMA_MAX = 22

class PerceptronApp:
    def __init__(self):
        self.device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
        self.config = ConfigManager(roles=['Z','A','B'], grupos_max=9, extra_fields={'valor':0})
        self.config.load()

        if self.config.get('role') is None:
            self.config.set('role', 'A')
        if self.config.get('grupo') is None:
            self.config.set('grupo', 0)
        if self.config.get('valor') is None:
            self.config.set('valor', 0)

        self.msg = RadioMessage(format="csv", activity=ACTIVITY, device_id=self.device_id)
        self.msg.set_context(group=self.config.get('grupo'), role=self.config.get('role'))

        self.suma_total = 0
        self.valor_a = 0
        self.valor_b = 0

        radio.on()
        g = self.config.get('grupo')
        radio.config(channel=g if g else 0, power=6, length=64, queue=10)

        r = self.config.get('role')
        if r:
            display.show(str(r))
            sleep(500)
        if g:
            display.show(str(g))
            sleep(500)
        display.clear()

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
        payload = str(vp)
        self.msg.send(radio.send, payload)
        print("TX:{}:v={},peso={},vp={}".format(self.config.get('role'), v, peso, vp))

    def rol_a(self):
        if button_a.was_pressed():
            self.actualizar_valor(-1, 1)
        if button_b.was_pressed():
            self.actualizar_valor(1, 1)

    def rol_b(self):
        if button_a.was_pressed():
            self.actualizar_valor(-1, 2)
        if button_b.was_pressed():
            self.actualizar_valor(1, 2)

    def rol_z(self):
        valid, sender, payload = self.msg.recibe_csv(radio.receive, valid_roles=['A','B'])
        if valid:
            print("RX:Z:sender={},payload={}".format(sender, payload))
            if sender and payload:
                try:
                    val = int(payload)
                    suma_anterior = self.suma_total

                    if sender == 'A':
                        self.valor_a = val
                    elif sender == 'B':
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
        if pin1.is_touched():
            if button_a.was_pressed():
                self.config.cycle_role()
                self.config.save()
                nr = self.config.get('role')
                self.msg.set_context(group=self.config.get('grupo'), role=nr)
                display.show(str(nr))
                sleep(1000)
                display.clear()
                button_a.was_pressed()
            elif button_b.was_pressed():
                self.config.cycle_grupo()
                self.config.save()
                ng = self.config.get('grupo')
                self.msg.set_context(group=ng, role=self.config.get('role'))
                if ng is not None:
                    radio.config(channel=ng, power=6, length=64, queue=10)
                display.show(str(ng))
                sleep(1000)
                display.clear()
                button_b.was_pressed()

    def mostrar_config(self):
        display.show(ACTIVITY)
        sleep(500)
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