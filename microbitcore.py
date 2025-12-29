# microbitcore.py
# Libreria de comunicacion radio para micro:bit
# Formatos: CSV (activity,group,role,payload) y Command (CMD:args)

class RadioMessage:
    def __init__(self, format="csv", activity=None, device_id=None):
        self.format = format
        self.activity = activity
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
            payload_escaped = str(payload).replace(",", "_coma_")
            if self.activity:
                return "{},{},{},{}".format(self.activity, self.group, self.role, payload_escaped)
            else:
                return "{},{},{}".format(self.group, self.role, payload_escaped)
        else:
            return str(payload)
    
    def decode(self, raw_msg, valid_roles=None):
        if not raw_msg:
            return {'t': 'empty', 'm': None, 'g': None, 'd': None}
        
        msg_str = raw_msg.decode('utf-8') if isinstance(raw_msg, bytes) else str(raw_msg)
        
        if self.format == "csv":
            partes = msg_str.split(',')
            
            # Detectar si tiene activity
            if self.activity and len(partes) == 4:
                activity_, grupo, rol, data = partes
                if activity_ != self.activity:
                    return {'t': 'activity_mismatch', 'm': None, 'g': None, 'd': None}
            elif len(partes) == 3:
                grupo, rol, data = partes
            else:
                return {'t': 'csv_invalid', 'm': None, 'g': None, 'd': msg_str}
            
            data_unescaped = data.replace("_coma_", ",")
            
            if valid_roles and rol not in valid_roles:
                return {'t': 'filtered', 'm': rol, 'g': grupo, 'd': data_unescaped}
            return {'t': 'csv_valid', 'm': rol, 'g': grupo, 'd': data_unescaped}
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
    
    def recibe_csv(self, radio_receive_fn, valid_roles=None):
        """Helper para recepcion simple de mensajes CSV
        Retorna: (valid, sender_role, payload)
        """
        m = self.receive(radio_receive_fn, valid_roles)
        if m and m['t'] == 'csv_valid':
            return (True, m.get('m'), m.get('d'))
        return (False, None, None)
    
    def recibe_command(self, radio_receive_fn, expected_types=None):
        """Helper para recepcion de comandos
        Retorna: (valid, tipo_comando, payload)
        """
        m = self.receive(radio_receive_fn)
        if m and expected_types and m['t'] in expected_types:
            return (True, m['t'], m['d'])
        elif m and not expected_types:
            return (True, m['t'], m['d'])
        return (False, None, None)
    
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
    
    def cycle_role(self):
        idx = self.roles.index(self.config['role']) if self.config['role'] in self.roles else 0
        idx = (idx + 1) % len(self.roles)
        self.config['role'] = self.roles[idx]
        return self.config['role']
    
    def cycle_grupo(self):
        self.config['grupo'] = (self.config['grupo'] + 1) % (self.grupos_max + 1)
        return self.config['grupo']