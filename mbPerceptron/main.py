# perceptron.py
from microbit import *
import radio
import music
import machine
from microbitcore import RadioMessage, ConfigManager

SUMA_MAX = 22

device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
config = ConfigManager(roles=['Z','A','B'], grupos_max=9, extra_fields={'valor':0})
config.load()

if config.get('role') is None:
    config.set('role', 'A')
if config.get('grupo') is None:
    config.set('grupo', 0)
if config.get('valor') is None:
    config.set('valor', 0)

msg = RadioMessage(format="csv", device_id=device_id)
msg.set_context(version="pct", group=config.get('grupo'), role=config.get('role'))

suma_total = 0
valor_a = 0
valor_b = 0

def mostrar_leds(n):
    if n == 0:
        display.clear()
        return
    n = min(n, 25)
    leds = ""
    for i in range(25):
        leds += "9" if i < n else "0"
    patron = "{}:{}:{}:{}:{}".format(leds[0:5], leds[5:10], leds[10:15], leds[15:20], leds[20:25])
    display.show(Image(patron))

def actualizar_valor(delta, peso=1):
    if pin1.is_touched():
        return
    v = config.get('valor')
    if v is None:
        v = 0
    v = (v + delta) % 10
    config.set('valor', v)
    config.save()
    vp = v * peso
    mostrar_leds(vp)
    radio.send(msg.encode(str(vp)))

def rol_a():
    if button_a.was_pressed():
        actualizar_valor(-1, 1)
    if button_b.was_pressed():
        actualizar_valor(1, 1)

def rol_b():
    if button_a.was_pressed():
        actualizar_valor(-1, 2)
    if button_b.was_pressed():
        actualizar_valor(1, 2)

def rol_z():
    global valor_a, valor_b, suma_total
    rx = radio.receive()
    if rx:
        decoded = msg.decode(rx, ['A','B'])
        
        if decoded['t'] == 'csv_valid':
            sender = decoded.get('m')
            payload = decoded.get('d')
            
            if sender and payload:
                try:
                    val = int(payload)
                    suma_anterior = suma_total
                    
                    if sender == 'A':
                        valor_a = val
                    elif sender == 'B':
                        valor_b = val
                    
                    suma_total = valor_a + valor_b
                    
                    if suma_total > SUMA_MAX:
                        suma_total = SUMA_MAX
                    
                    if suma_total == SUMA_MAX and suma_anterior != SUMA_MAX:
                        music.pitch(frequency=500, duration=250, wait=False)
                    
                    mostrar_leds(suma_total)
                except:
                    pass

def cambiar_config():
    global msg
    if pin1.is_touched():
        if button_a.was_pressed():
            config.cycle_role()
            config.save()
            nr = config.get('role')
            msg.set_context(role=nr)
            display.show(str(nr))
            sleep(1000)
            display.clear()
            button_a.was_pressed()
        elif button_b.was_pressed():
            config.cycle_grupo()
            config.save()
            ng = config.get('grupo')
            msg.set_context(group=ng)
            if ng is not None:
                radio.config(chn=ng, power=6, length=64, queue=10)
            display.show(str(ng))
            sleep(1000)
            display.clear()
            button_b.was_pressed()

def mostrar_config():
    r = config.get('role')
    g = config.get('grupo')
    if r is not None:
        display.show(str(r))
        sleep(500)
    if g is not None:
        display.show(str(g))
        sleep(500)
    display.clear()

radio.on()
g = config.get('grupo')
radio.config(chn=g if g else 0, power=6, length=64, queue=10)

r = config.get('role')
if r:
    display.show(str(r))
    sleep(500)
if g:
    display.show(str(g))
    sleep(500)
display.clear()

while True:
    cambiar_config()
    if pin_logo.is_touched():
        mostrar_config()
    if not pin1.is_touched():
        ra = config.get('role')
        if ra == 'A':
            rol_a()
        elif ra == 'B':
            rol_b()
        elif ra == 'Z':
            rol_z()
    sleep(50)