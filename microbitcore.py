# microbitcore.py
# Libreria de comunicacion radio para micro:bit
# Formatos: CSV (group,role,payload) y Command (CMD:args)

class RadioMessage:
    def __init__(self, format="csv", device_id=None):
        self.format = format
        self.device_id = device_id
        self.group = None
        self.role = None
    
    def set_context(self, group, role):
        self.group = str(group)
        self.role = str(role)
    
    def encode(self, payload):
        if self.format == "csv":
            if self.group is None or self.role is None:
                return None
            return "{},{},{}".format(self.group, self.role, str(payload))
        else:
            return str(payload)
    
    def decode(self, raw_msg, valid_roles=None):
        if not raw_msg:
            return {'t': 'empty', 'm': None, 'g': None, 'd': None}
        
        msg_str = raw_msg.decode('utf-8') if isinstance(raw_msg, bytes) else str(raw_msg)
        
        if self.format == "csv":
            partes = msg_str.split(',', 2)
            if len(partes) == 3:
                grupo, rol, data = partes
                if valid_roles and rol not in valid_roles:
                    return {'t': 'filtered', 'm': rol, 'g': grupo, 'd': data}
                return {'t': 'csv_valid', 'm': rol, 'g': grupo, 'd': data}
            else:
                return {'t': 'csv_invalid', 'm': None, 'g': None, 'd': msg_str}
        else:
            return {'t': msg_str.split(':')[0] if ':' in msg_str else msg_str, 
                    'm': None, 'g': None, 'd': msg_str}
    
    def send(self, radio_send_fn, payload):
        encoded = self.encode(payload)
        if encoded:
            radio_send_fn(encoded)
    
    def receive(self, radio_receive_fn, valid_roles=None):
        raw = radio_receive_fn()
        if raw:
            return self.decode(raw, valid_roles)
        return None
    
    def parse_payload(self, payload):
        if not payload:
            return (None, [])
        partes = str(payload).split(':')
        return (partes[0], partes[1:] if len(partes) > 1 else [])
    
    def is_for_me(self, message):
        if not self.device_id or not message:
            return False
        tipo, args = self.parse_payload(message)
        if args and len(args) > 0:
            return args[0] == self.device_id
        return False
    
    def extract_device_id(self, message):
        tipo, args = self.parse_payload(message)
        return args[0] if args else None
    
    def extract_answer(self, message):
        tipo, args = self.parse_payload(message)
        if len(args) >= 2:
            device = args[0]
            opciones = args[1].split(',') if ',' in args[1] else [args[1]]
            return (device, opciones)
        return (None, [])
    
    def extract_qparams(self, message):
        tipo, args = self.parse_payload(message)
        if len(args) >= 2:
            return (args[0], int(args[1]))
        return (None, None)
    
    def cmd_report(self):
        return "REPORT"
    
    def cmd_id(self):
        return "ID:{}".format(self.device_id) if self.device_id else "ID"
    
    def cmd_ack(self, target_id):
        return "ACK:{}".format(target_id)
    
    def cmd_ping(self, target_id):
        return "PING:{}".format(target_id)
    
    def cmd_pong(self):
        return "PONG:{}".format(self.device_id) if self.device_id else "PONG"
    
    def cmd_poll(self, target_id):
        return "POLL:{}".format(target_id)
    
    def cmd_vote(self, opcion):
        return "VOTE:{}:{}".format(self.device_id, opcion) if self.device_id else "VOTE:{}".format(opcion)
    
    def cmd_answer(self, *opciones):
        opciones_str = ','.join(str(o) for o in opciones)
        return "ANSWER:{}:{}".format(self.device_id, opciones_str) if self.device_id else "ANSWER:{}".format(opciones_str)
    
    def cmd_qparams(self, tipo_pregunta, num_opciones):
        return "QPARAMS:{}:{}".format(tipo_pregunta, num_opciones)
    
    def command(self, cmd, *args):
        if args:
            return "{}:{}".format(cmd, ':'.join(str(a) for a in args))
        return cmd


class ConfigManager:
    def __init__(self, config_file='config.cfg', roles=None, grupos_max=9, extra_fields=None):
        self.config_file = config_file
        self.roles = roles or ['A', 'B', 'Z']
        self.grupos_max = grupos_max
        self.config = {
            'role': self.roles[0],
            'grupo': 0
        }
        if extra_fields:
            self.config.update(extra_fields)
    
    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                lineas = f.read().strip().split('\n')
                for linea in lineas:
                    if '=' in linea:
                        key, val = linea.split('=', 1)
                        key = key.strip()
                        val = val.strip()
                        if key in self.config:
                            if key == 'grupo':
                                self.config[key] = int(val)
                            elif val == 'None':
                                self.config[key] = None
                            else:
                                try:
                                    self.config[key] = int(val)
                                except:
                                    self.config[key] = val
            return True
        except:
            return False
    
    def save(self):
        try:
            lineas = []
            for key, val in self.config.items():
                lineas.append("{}={}".format(key, val))
            with open(self.config_file, 'w') as f:
                f.write('\n'.join(lineas))
            return True
        except:
            return False
    
    def get(self, key):
        return self.config.get(key)
    
    def set(self, key, value):
        if key in self.config:
            self.config[key] = value
    
    def get_all(self):
        return self.config.copy()
    
    def cycle_role(self):
        idx = self.roles.index(self.config['role']) if self.config['role'] in self.roles else 0
        idx = (idx + 1) % len(self.roles)
        self.config['role'] = self.roles[idx]
        return self.config['role']
    
    def cycle_grupo(self):
        self.config['grupo'] = (self.config['grupo'] + 1) % (self.grupos_max + 1)
        return self.config['grupo']
    
    def reset(self):
        self.config['role'] = self.roles[0]
        self.config['grupo'] = 0
        for key in self.config:
            if key not in ['role', 'grupo']:
                self.config[key] = None
    
    def display_config(self, display, delay_ms=500):
        from microbit import sleep
        display.show(str(self.config['role']))
        sleep(delay_ms)
        display.show(str(self.config['grupo']))
        sleep(delay_ms)
        display.clear()