# concentrador.py
from microbit import *
from microbitml import Radio

ACTIVITY = "con"
CHANNEL  = 0

class Concentrador:
    def __init__(self):
        self.radio = Radio(activity=ACTIVITY, channel=CHANNEL)
        uart.init(baudrate=115200)

    def enviar_usb(self, msg):
        print(msg)

    def radio_a_json(self, msg):
        # Serializa campos del Message a JSON minimo sin librerias
        valores_str = ""
        if msg.valores:
            valores_str = '","'.join(msg.valores)
            valores_str = '["' + valores_str + '"]'
        else:
            valores_str = "[]"

        act_str    = ',"act":"{}"'.format(msg.act) if msg.act else ""
        devid_str  = ',"devID":"{}"'.format(msg.devID) if msg.devID else ""
        grp_str    = ',"grp":{}'.format(msg.grp)       if msg.grp is not None else ""
        rol_str    = ',"rol":"{}"'.format(msg.rol)     if msg.rol else ""

        return '{{"name":"{}"{}{}{}{}, "valores":{}}}'.format(
            msg.name, act_str, devid_str, grp_str, rol_str, valores_str
        )

    def json_a_radio(self, linea):
        # Parseo manual del JSON que manda la PC
        # Extrae campos y construye el payload radio
        def extraer(campo, texto):
            marca = '"{}":'.format(campo)
            idx = texto.find(marca)
            if idx == -1:
                return None
            inicio = idx + len(marca)
            if texto[inicio] == '"':
                fin = texto.index('"', inicio + 1)
                return texto[inicio + 1:fin]
            elif texto[inicio] == '[':
                fin = texto.index(']', inicio)
                return texto[inicio:fin + 1]
            else:
                fin = inicio
                while fin < len(texto) and texto[fin] not in (',', '}'):
                    fin += 1
                return texto[inicio:fin].strip()

        name   = extraer("name",   linea)
        act    = extraer("act",    linea)
        devid  = extraer("devID",  linea)
        grp    = extraer("grp",    linea)
        rol    = extraer("rol",    linea)
        valores_raw = extraer("valores", linea)

        if not name:
            return

        # Armar valores como string separado por coma
        valores_str = ""
        if valores_raw and valores_raw != "[]":
            # quitar corchetes y comillas
            inner = valores_raw.strip("[]").replace('"', '')
            valores_str = inner  # ya viene separado por coma

        # Sanitizar: quitar comillas residuales si el parser falla
        name  = name.strip('"')  if name  else name
        act   = act.strip('"')   if act   else act
        devid = devid.strip('"') if devid else devid
        rol   = rol.strip('"')   if rol   else rol

        # Determinar sufijo y args segun campos presentes
        if devid and grp is not None and rol:
            sufijo = "_DGR"
            base = "{}:{}:{}:{}".format(name + sufijo, devid, grp, rol)
        elif grp is not None and rol:
            sufijo = "_GR"
            base = "{}:{}:{}".format(name + sufijo, grp, rol)
        else:
            base = name

        # Usa la actividad que envio la PC, si no viene usa la propia
        prefijo = act if act else ACTIVITY
        payload = prefijo + ":" + base
        if valores_str:
            payload += ":" + valores_str

        self.radio.send(payload, CMD=False)

    def manejar_radio(self):
        msg = self.radio.receive(full=True)
        if not msg.valid or not msg.name:
            return
        try:
            self.enviar_usb(self.radio_a_json(msg))
        except Exception as e:
            self.enviar_usb('{{"error":"{}"}}'.format(str(e)))

    def manejar_usb(self):
        if uart.any():
            try:
                linea = uart.readline()
                if linea:
                    linea = linea.decode('utf-8').strip()
                    if linea:
                        self.json_a_radio(linea)
            except:
                pass

    def manejar_botones(self):
        if button_a.was_pressed():
            self.enviar_usb('{"event":"button_a"}')
        if button_b.was_pressed():
            self.enviar_usb('{"event":"button_b"}')
        if pin_logo.is_touched():
            self.enviar_usb('{"event":"logo_touch"}')

    def run(self):
        self.enviar_usb('{"event":"gateway_ready"}')
        display.show(Image.HAPPY)
        sleep(1000)
        display.clear()

        while True:
            self.manejar_botones()
            self.manejar_radio()
            self.manejar_usb()
            sleep(50)

Concentrador().run()