#
# microbit-module: microbitml@1.0.0
#
# ---
# microbitml.py
# Libreria de comunicacion radio para micro:bit

from microbit import display, sleep
import radio
import machine

# Objeto retornado por receive()
class Message:
    def __init__(self):
        self.valid = False
        self.act = None
        self.name = None
        self.devID = None
        self.grp = None
        self.rol = None
        self.valores = []

    def _reset(self):
        self.valid = False
        self.act = None
        self.name = None
        self.devID = None
        self.grp = None
        self.rol = None
        self.valores = []


# Manejo de comunicacion radio
class Radio:
    def __init__(self, activity='mbtml', channel=0):
        self.activity = activity[:5]
        self.device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
        self.group = 0
        self.role = 'A'
        self.channel = channel
        self.radio = radio
        self._resultado = Message()
        radio.on()
        radio.config(channel=channel, power=6, length=64, queue=10)

    # Asigna grupo, rol y canal
    def configure(self, group, role, channel=None):
        self.group = str(group)
        self.role = str(role)
        if channel is not None and channel != self.channel:
            self.channel = channel
            radio.config(channel=channel, power=6, length=64, queue=10)

    # Envia mensaje por radio
    def send(self, name, *args, device_id=False, packed=False, CMD=True):
        if CMD:
            s = '_DGR' if device_id else '_GR'
            payload = self.activity + ':' + self.cmd(name + s, *args, device_id=device_id, gr=True, packed=packed)
        else:
            payload = name
        radio.send(str(payload))

    def _read(self):
        raw = radio.receive()
        if not raw:
            return None
        msg_str = str(raw)
        #print("RAW:{}".format(msg_str))
        tipo = msg_str.split(':')[0] if ':' in msg_str else msg_str
        return {'t': tipo, 'd': msg_str}

    # Recibe un mensaje, retorna Message
    # full=True: acepta mensajes de cualquier grupo (para concentrador)
    def receive(self, filter=None, full=False):
        r = self._resultado
        r._reset()
        m = self._read()
        if not m:
            return r
        all_parts, args = self._parse(m['d'])
        if not all_parts or len(args) < 1:
            return r
        r.act = all_parts
        if r.act != self.activity:
            if not (str(self.group) == '0' and str(self.role) == 'A'):
                return r
        tipo = args[0]
        args = args[1:]
        sufijos = ('_DGR', '_GR')
        sufijo = ''
        for s in sufijos:  # la primitiva next() de microPython no acepta el parámetro default
            if tipo.endswith(s):
                sufijo = s
                break # es ésto o un try-except(StopIteration), perdón Niklaus
        r.name = tipo[:-len(sufijo)] if sufijo else tipo
        expected = [filter] if isinstance(filter, str) else filter
        if expected and r.name not in expected:
            return r
        vr = None
        if sufijo == '_DGR':
            if len(args) < 3: return r
            r.devID, r.grp, r.rol = args[0], self._to_int(args[1]), args[2]
            if len(args) >= 4: vr = args[3]
        elif sufijo == '_GR':
            if len(args) < 2: return r
            r.grp, r.rol = self._to_int(args[0]), args[1]
            if len(args) >= 3: vr = args[2]
        else:
            if len(args) >= 1: vr = ','.join(str(a) for a in args)
        if not full and r.grp is not None:
            if r.grp != 0 and str(r.grp) != str(self.group):
                return r
        if vr is not None:
            r.valores = vr.split(',') if ',' in vr else [vr]
        r.valid = True
        return r

    def _parse(self, payload):
        if not payload:
            return (None, [])
        partes = str(payload).split(':')
        return (partes[0], partes[1:] if len(partes) > 1 else [])

    def _build(self, cmd, *args):
        if args:
            return "{}:{}".format(cmd, ':'.join(str(a) for a in args))
        return cmd

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

    def _to_int(self, x):
        try:
            return int(x)
        except:
            return x


# Persistencia de configuracion en flash
class ConfigManager:
    def __init__(self, config_file='config.cfg', roles=None, grupos_max=9, grupos_min=1, extra_fields=None):
        self.config_file = config_file
        self.roles = roles or ['A', 'B', 'Z']
        self.grupos_max = grupos_max
        self.grupos_min = grupos_min
        self.config = {'role': self.roles[0], 'grupo': self.grupos_min}
        if extra_fields:
            self.config.update(extra_fields)

    # Carga config desde archivo
    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                content = f.read().strip()
            if not content:
                return False
            for linea in content.split('\n'):
                if '=' in linea:
                    k, v = linea.split('=', 1)
                    k, v = k.strip(), v.strip()
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
            #print("CFG:Error:{}".format(str(e)))
            return False

    # Guarda config en archivo
    def save(self):
        try:
            f = open(self.config_file, 'w')
            for k in self.config:
                f.write("{}={}\n".format(k, self.config[k]))
            f.close()
            return True
        except:
            return False

    # Obtiene un valor de config
    def get(self, key):
        return self.config.get(key)

    # Modifica un valor de config
    def set(self, key, value):
        if key in self.config:
            self.config[key] = value

    # Avanza al siguiente rol
    def next_role(self):
        idx = self.roles.index(self.config['role']) if self.config['role'] in self.roles else 0
        self.config['role'] = self.roles[(idx + 1) % len(self.roles)]
        return self.config['role']

    # Avanza al siguiente grupo
    def next_group(self):
        g = self.config.get('grupo', self.grupos_min)
        rango = self.grupos_max - self.grupos_min + 1
        self.config['grupo'] = ((g - self.grupos_min + 1) % rango) + self.grupos_min
        return self.config['grupo']

    # Modo configuracion: pin1 + botones A/B
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
                if cb: cb()
                while ba.is_pressed(): sleep(50)
            if bb.was_pressed():
                self.next_group()
                self.save()
                changed = True
                if cb: cb()
                while bb.is_pressed(): sleep(50)
            sleep(50)
        display.clear()
        sleep(200)
        return changed