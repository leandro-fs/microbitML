#
# microbit-module: microbitml@1.0.0
#
# ---
# microbitml.py
# Libreria de comunicacion radio para micro:bit
# Formatos: CSV (activity,group,role,payload) y Command (CMD:args)

from microbit import display, sleep
import radio
import machine


# Objeto reutilizable que retorna receive()
# Siempre es la misma instancia, se resetea en cada llamada
class Message:
    def __init__(self):
        self.valid = False   # True si se recibio un mensaje valido
        self.name = None     # Tipo de comando (ej: 'ID', 'POLL')
        self.devID = None    # device_id del emisor
        self.grp = None      # grupo del emisor
        self.rol = None      # rol del emisor
        self.valores = []    # lista de valores del payload

    def _reset(self):
        # Limpia el objeto sin crear uno nuevo
        self.valid = False
        self.name = None
        self.devID = None
        self.grp = None
        self.rol = None
        self.valores = []


class Radio:
    def __init__(self, activity='mbtml', channel=0):
        self.activity = activity
        self.device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
        self.group = None
        self.role = None
        self.channel = channel
        self._resultado = Message()  # instancia unica reutilizable

        radio.on()
        radio.config(channel=channel, power=6, length=64, queue=10)

    # Configura grupo, rol y canal
    def configure(self, group, role, channel=None):
        self.group = str(group)
        self.role = str(role)
        if channel is not None and channel != self.channel:
            self.channel = channel
            radio.config(channel=channel, power=6, length=64, queue=10)

    # Envia mensaje por radio
    # CMD=True (default): construye comando formateado con cmd()
    # CMD=False: envia el string literal sin procesar
    # Nota: device_id, gr, packed se ignoran si CMD=False
    def send(self, name, *args, device_id=False, gr=False, packed=False, CMD=True):
        if CMD:
            payload = self.cmd(name, *args, device_id=device_id, gr=gr, packed=packed)
        else:
            payload = name
        radio.send(str(payload))

    # Lee un mensaje raw de radio y retorna dict {t: tipo, d: mensaje_completo}
    def _read(self):
        raw = radio.receive()
        if not raw:
            return None
        msg_str = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
        tipo = msg_str.split(':')[0] if ':' in msg_str else msg_str
        return {'t': tipo, 'd': msg_str}

    # Recibe un mensaje y retorna el objeto Message reutilizable
    # filter: None (todo) | str | list de tipos de comando
    # Estructura del mensaje esperada segun cantidad de args:
    #   4 args -> devID:grp:rol:valores
    #   3 args -> grp:rol:valores
    #   2 args -> devID:valores
    #   1 arg  -> valores
    def receive(self, filter=None):
        r = self._resultado
        r._reset()

        m = self._read()
        if not m:
            return r

        # Filtrar por tipo de comando
        expected_types = [filter] if isinstance(filter, str) else filter
        if expected_types and m['t'] not in expected_types:
            return r

        tipo, args = self._parse(m['d'])
        r.name = tipo

        if len(args) >= 4:
            r.devID = args[0]
            r.grp = self._to_int(args[1])
            r.rol = args[2]
            valores_raw = args[3]
        elif len(args) >= 3:
            r.grp = self._to_int(args[0])
            r.rol = args[1]
            valores_raw = args[2]
        elif len(args) >= 2:
            r.devID = args[0]
            valores_raw = args[1]
        elif len(args) == 1:
            valores_raw = args[0]
        else:
            r.valid = True
            return r

        r.valores = valores_raw.split(',') if ',' in valores_raw else [valores_raw]
        r.valid = True
        return r

    # Parsea payload y retorna (tipo, [args])
    def _parse(self, payload):
        if not payload:
            return (None, [])
        partes = str(payload).split(':')
        return (partes[0], partes[1:] if len(partes) > 1 else [])

    # Verifica si el mensaje esta dirigido a este device_id
    def addressed_to_me(self, message):
        if not self.device_id or not message:
            return False
        tipo, args = self._parse(message)
        return args and len(args) > 0 and args[0] == self.device_id

    # Extrae device_id del primer argumento del mensaje
    def _sender_id(self, message):
        tipo, args = self._parse(message)
        return args[0] if args else None

    # Extrae (tipo_pregunta, num_opciones) de un mensaje QPARAMS
    def _qparams(self, message):
        tipo, args = self._parse(message)
        if len(args) >= 2:
            return (args[0], int(args[1]))
        return (None, None)

    # Construye string de comando: CMD:arg1:arg2:...
    def _build(self, cmd, *args):
        if args:
            return "{}:{}".format(cmd, ':'.join(str(a) for a in args))
        return cmd

    # Construye comando con opciones:
    #   device_id: incluye self.device_id al inicio
    #   gr: incluye self.group y self.role
    #   packed: une multiples args con coma en un solo campo
    def cmd(self, name, *args, device_id=False, gr=False, packed=False):
        params = []

        if device_id and self.device_id:
            params.append(self.device_id)
        if gr:
            if self.group:
                params.append(self.group)
            if self.role:
                params.append(self.role)

        if packed:
            if len(args) == 1 and isinstance(args[0], (list, tuple)):
                args = (','.join(str(a) for a in args[0]),)
            else:
                args = (','.join(str(a) for a in args),)

        params.extend(args)
        return self._build(name, *params)

    # Convierte a int si es posible, sino retorna el valor original
    def _to_int(self, x):
        try:
            return int(x)
        except:
            return x


class ConfigManager:
    def __init__(self, config_file='config.cfg', roles=None, grupos_max=9, grupos_min=0, extra_fields=None):
        self.config_file = config_file
        self.roles = roles or ['A', 'B', 'Z']
        self.grupos_max = grupos_max
        self.grupos_min = grupos_min
        self.config = {
            'role': self.roles[0],
            'grupo': self.grupos_min
        }
        if extra_fields:
            self.config.update(extra_fields)

    # Carga configuracion desde archivo, retorna True si exitoso
    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                content = f.read().strip()
            if not content:
                return False
            for linea in content.split('\n'):
                if '=' in linea:
                    k, v = linea.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if k in self.config:
                        if k == 'grupo':
                            self.config[k] = int(v)
                        elif v == 'None':
                            self.config[k] = None
                        else:
                            try:
                                self.config[k] = int(v)
                            except:
                                self.config[k] = v
            return True
        except Exception as e:
            print("CFG:Error:{}".format(str(e)))
            return False

    # Guarda configuracion en archivo, retorna True si exitoso
    def save(self):
        try:
            f = open(self.config_file, 'w')
            for k in self.config:
                f.write("{}={}\n".format(k, self.config[k]))
            f.close()
            return True
        except:
            return False

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        if key in self.config:
            self.config[key] = value

    # Avanza al siguiente rol en la lista de roles
    def next_role(self):
        idx = self.roles.index(self.config['role']) if self.config['role'] in self.roles else 0
        idx = (idx + 1) % len(self.roles)
        self.config['role'] = self.roles[idx]
        return self.config['role']

    # Avanza al siguiente grupo dentro del rango configurado
    def next_group(self):
        g = self.config.get('grupo', self.grupos_min)
        rango = self.grupos_max - self.grupos_min + 1
        g = ((g - self.grupos_min + 1) % rango) + self.grupos_min
        self.config['grupo'] = g
        return g

    # Modo configuracion: mantener p1 tocado, A cambia rol, B cambia grupo
    # cb: callback opcional que se llama tras cada cambio
    def config_rg(self, p1, ba, bb, cb=None):
        if not p1.is_touched():
            return False
        sleep(200)
        changed = False
        while p1.is_touched():
            if ba.was_pressed():
                self.next_role()
                self.save()
                changed = True
                if cb:
                    cb()
                while ba.is_pressed():
                    sleep(50)

            if bb.was_pressed():
                self.next_group()
                self.save()
                changed = True
                if cb:
                    cb()
                while bb.is_pressed():
                    sleep(50)
            sleep(50)
        display.clear()
        sleep(200)
        return changed