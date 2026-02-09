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

class RadioMessage:
    def __init__(self, activity='mbtml', channel=0):
        self.activity = activity
        self.device_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])
        self.group = None
        self.role = None
        self.channel = channel
        
        radio.on()
        radio.config(channel=channel, power=6, length=64, queue=10)
    
    def configure(self, group, role, channel=None):
        """Configura grupo, rol y canal"""
        self.group = str(group)
        self.role = str(role)
        if channel is not None and channel != self.channel:
            self.channel = channel
            radio.config(channel=channel, power=6, length=64, queue=10)
    
    def send(self, payload):
        """Envia payload por radio"""
        radio.send(str(payload))
    
    def receive(self):
        """Recibe mensaje raw de radio y retorna dict parseado"""
        raw = radio.receive()
        if not raw:
            return None
        
        msg_str = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
        
        # Parsear comando
        tipo = msg_str.split(':')[0] if ':' in msg_str else msg_str
        return {'t': tipo, 'd': msg_str}
    
    def recibe(self, filter=None, unpack=False):
        """
        filter: None (todo) | str | list de tipos comando
        unpack: descompone payload packed
        
        Retorna:
          unpack=False: (valid, tipo, payload)
          unpack=True:  (valid, tipo, device_id, grupo, role, [valores])
        """
        m = self.receive()
        
        if not m:
            return (False, None, None) if not unpack else (False, None, None, None, None, [])
        
        # Filtrar por tipo
        expected_types = [filter] if isinstance(filter, str) else filter
        
        if expected_types and m['t'] not in expected_types:
            return (False, None, None) if not unpack else (False, None, None, None, None, [])
        
        if not unpack:
            return (True, m['t'], m['d'])
        
        # Unpack
        tipo, args = self.parse_payload(m['d'])
        dev = grp = rol = None
        valores = []
        
        if len(args) >= 4:
            dev, grp, rol, valores_raw = args[0], self._to_int(args[1]), args[2], args[3]
        elif len(args) >= 3:
            grp, rol, valores_raw = self._to_int(args[0]), args[1], args[2]
        elif len(args) >= 2:
            dev, valores_raw = args[0], args[1]
        elif len(args) == 1:
            valores_raw = args[0]
        else:
            return (True, tipo, dev, grp, rol, valores)
        
        valores = valores_raw.split(',') if ',' in valores_raw else [valores_raw]
        
        return (True, tipo, dev, grp, rol, valores)
    
    def parse_payload(self, payload):
        """Retorna (tipo, [args])"""
        if not payload:
            return (None, [])
        partes = str(payload).split(':')
        return (partes[0], partes[1:] if len(partes) > 1 else [])
    
    def is_for_me(self, message):
        """Verifica si mensaje es para este device_id"""
        if not self.device_id or not message:
            return False
        tipo, args = self.parse_payload(message)
        return args and len(args) > 0 and args[0] == self.device_id
    
    def extract_device_id(self, message):
        """Extrae device_id del mensaje"""
        tipo, args = self.parse_payload(message)
        return args[0] if args else None
    
    def extract_qparams(self, message):
        """Extrae (tipo_pregunta, num_opciones)"""
        tipo, args = self.parse_payload(message)
        if len(args) >= 2:
            return (args[0], int(args[1]))
        return (None, None)
    
    def command(self, cmd, *args):
        """Genera comando: CMD:arg1:arg2"""
        if args:
            return "{}:{}".format(cmd, ':'.join(str(a) for a in args))
        return cmd
    
    def cmd(self, name, *args, device_id=False, gr=False, packed=False):
        """
        Genera comando con opciones:
        - device_id: incluye self.device_id
        - gr: incluye self.group y self.role
        - packed: une args con coma
        """
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
        return self.command(name, *params)
    
    def _to_int(self, x):
        """Convierte a int si es posible"""
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
    
    def cycle_role(self):
        idx = self.roles.index(self.config['role']) if self.config['role'] in self.roles else 0
        idx = (idx + 1) % len(self.roles)
        self.config['role'] = self.roles[idx]
        return self.config['role']
    
    def cycle_grupo(self):
        g = self.config.get('grupo', self.grupos_min)
        rango = self.grupos_max - self.grupos_min + 1
        g = ((g - self.grupos_min + 1) % rango) + self.grupos_min
        self.config['grupo'] = g
        return g
    
    def config_rg(self, p1, ba, bb, cb=None):
        if not p1.is_touched():
            return False
        sleep(200)
        changed = False
        while p1.is_touched():
            if ba.was_pressed():
                self.cycle_role()
                self.save()
                changed = True
                if cb:
                    cb()
                while ba.is_pressed():
                    sleep(50)
            
            if bb.was_pressed():
                self.cycle_grupo()
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