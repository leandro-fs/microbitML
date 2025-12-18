__all__ = ["RadioMessage", "MultichnManager", "ConfigManager"]

class RadioMessage:
    def __init__(self, format="csv", device_id=None, role=None):
        self.format = format
        self.device_id = device_id
        self.role = role
        self.version_token = None
        self.group = None
        self.registered = False

    def set_context(self, version=None, group=None, role=None):
        if version:
            self.version_token = version
        if group is not None:
            self.group = group
        if role:
            self.role = role

    def set_device_id(self, device_id):
        self.device_id = device_id

    def encode(self, payload):
        if self.format == "csv":
            return self._encode_csv(payload)
        elif self.format == "command":
            raise ValueError("Use command()")
        else:
            raise ValueError("Formato no soportado")

    def _encode_csv(self, payload):
        if not self.version_token or self.group is None or not self.role:
            raise ValueError("Contexto incompleto")
        enc = self.version_token + ","
        enc += "{},".format(self.group)
        enc += "{},".format(self.role)
        enc += str(payload).replace(",", "_coma_")
        return enc

    def command(self, cmd, *params):
        if not params:
            return cmd
        return "{}:{}".format(cmd, ':'.join(str(x) for x in params))

    def cmd_report(self): return "REPORT"

    def cmd_id(self):
        if not self.device_id:
            raise ValueError("device_id requerido")
        return self.command("ID", self.device_id)

    def cmd_ack(self, device_id): return self.command("ACK", device_id)
    def cmd_ping(self, device_id): return self.command("PING", device_id)

    def cmd_pong(self):
        if not self.device_id:
            raise ValueError("device_id requerido")
        return self.command("PONG", self.device_id)

    def cmd_qparams(self, tipo, num_opciones): return self.command("QPARAMS", tipo, num_opciones)
    def cmd_poll(self, device_id): return self.command("POLL", device_id)

    def cmd_vote(self, opcion):
        if not self.device_id:
            raise ValueError("device_id requerido")
        return self.command("VOTE", self.device_id, opcion)

    def cmd_answer(self, *opciones):
        if not self.device_id:
            raise ValueError("device_id requerido")
        return self.command("ANSWER", self.device_id, ','.join(opciones))

    def cmd_consensus(self, grupo_id, opcion): return self.command("ANSWER", grupo_id, opcion)

    def cmd_warning(self, razon):
        if not self.device_id:
            raise ValueError("device_id requerido")
        return self.command("WARNING", self.device_id, razon)

    def decode(self, message, valid_roles=None):
        if not message:
            return {'t': None}
        if ',' in message and len(message.split(',')) >= 3:
            return self._decode_csv(message, valid_roles)
        return self._decode_command(message)

    def _decode_csv(self, message, valid_roles=None):
        res = {}
        ok = False
        st = ""
        role = ""
        pay = ""
        p = message.split(",")
        try:
            if len(p) != 4:
                st = "invalid_format"
                raise ValueError
            if self.version_token and p[0] != self.version_token:
                st = "version_mismatch"
                raise ValueError
            if self.group is not None and p[1] != str(self.group):
                st = "group_mismatch"
                raise ValueError
            role = p[2]
            if valid_roles and role not in valid_roles:
                st = "invalid_origin_role"
                raise ValueError
            pay = p[3].replace("_coma_", ",")
            ok = True
            st = "OK"
        except:
            pass
        res['t'] = 'csv_valid' if ok else 'csv_invalid'
        if pay:  res['d'] = pay
        if role: res['m'] = role
        if st:   res['s'] = st
        return res

    def _decode_command(self, message):
        res = {}
        if message == "REPORT":
            res['t'] = "REPORT"
            return res
        if ':' in message:
            p = message.split(':', 1)
            res['t'] = p[0]
            if len(p) > 1 and p[1]:
                res['d'] = p[1]
        else:
            res['t'] = message
        return res

    def extract_device_id(self, message):
        d = self.decode(message)
        if d['t'] in ["ID", "ACK", "PING", "PONG", "POLL"]:
            dev = d.get('d')
            return dev if dev else None
        return None

    def extract_vote(self, message):
        d = self.decode(message)
        x = d.get('d')
        if d['t'] == "VOTE" and x:
            p = x.split(':', 1)
            if len(p) == 2:
                return (p[0], p[1])
        return (None, None)

    def extract_answer(self, message):
        d = self.decode(message)
        x = d.get('d')
        if d['t'] == "ANSWER" and x:
            p = x.split(':', 1)
            if len(p) == 2:
                return (p[0], p[1].split(',') if p[1] else [])
        return (None, None)

    def extract_qparams(self, message):
        d = self.decode(message)
        x = d.get('d')
        if d['t'] == "QPARAMS" and x:
            p = x.split(':')
            if len(p) == 2:
                return (p[0], int(p[1]))
        return (None, None)

    def extract_warning(self, message):
        d = self.decode(message)
        x = d.get('d')
        if d['t'] == "WARNING" and x:
            p = x.split(':', 1)
            if len(p) == 2:
                return (p[0], p[1])
        return (None, None)

    def validate_for_me(self, message):
        return self.extract_device_id(message) == self.device_id


class MultichnManager:
    def __init__(self, radio_module):
        self.radio = radio_module
        self.chn_priv = None
        self.chn_pub = None
        self.current_chn = None

    def set_chns(self, private=None, public=None):
        self.chn_priv = private
        self.chn_pub = public
        if private:
            self.switch_to("private")

    def switch_to(self, chn_name):
        if chn_name == "private" and self.chn_priv:
            if self.current_chn != self.chn_priv:
                self.radio.config(chn=self.chn_priv)
                self.current_chn = self.chn_priv
        elif chn_name == "public" and self.chn_pub:
            if self.current_chn != self.chn_pub:
                self.radio.config(chn=self.chn_pub)
                self.current_chn = self.chn_pub

    def send(self, message, chn="private"):
        self.switch_to(chn)
        self.radio.send(message)

    def receive(self, chn="private"):
        self.switch_to(chn)
        return self.radio.receive()

    def receive_any(self, timeout_ms=500, check_order=None):
        from microbit import sleep, running_time
        if not check_order:
            check_order = ["private", "public"]
        slot = timeout_ms // len(check_order)
        for ch in check_order:
            self.switch_to(ch)
            tch = running_time()
            while running_time() - tch < slot:
                msg = self.radio.receive()
                if msg:
                    return (msg, ch)
                sleep(10)
        return (None, None)

    def flush_queue(self, chn=None):
        if chn:
            self.switch_to(chn)
            while self.radio.receive():
                pass
        else:
            for ch in ["private", "public"]:
                self.switch_to(ch)
                while self.radio.receive():
                    pass


class ConfigManager:
    def __init__(self, config_file='config.cfg', roles=None, grupos_max=9, extra_fields=None):
        self.config_file = config_file
        self.roles = roles if roles else ['A', 'B', 'Z']
        self.grupos_max = grupos_max
        self.config = {'role': self.roles[0], 'grupo': 0}
        if extra_fields:
            for k, v in extra_fields.items():
                self.config[k] = v

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def load(self):
        try:
            with open(self.config_file, 'r') as f:
                ld = eval(f.read())
            if 'role' in ld and 'grupo' in ld:
                for k in self.config.keys():
                    if k in ld:
                        self.config[k] = ld[k]
                return True
            return False
        except:
            return False

    def save(self):
        try:
            with open(self.config_file, 'w') as f:
                f.write(repr(self.config))
            return True
        except:
            return False

    def cycle_role(self):
        cur = self.config['role']
        try:
            i = self.roles.index(cur)
            self.config['role'] = self.roles[(i + 1) % len(self.roles)]
        except:
            self.config['role'] = self.roles[0]
        return self.config['role']

    def cycle_grupo(self):
        cur = self.config['grupo']
        self.config['grupo'] = (cur + 1) % (self.grupos_max + 1)
        return self.config['grupo']

    def set_role(self, role):
        if role in self.roles:
            self.config['role'] = role
            return True
        return False

    def set_grupo(self, grupo):
        if 0 <= grupo <= self.grupos_max:
            self.config['grupo'] = grupo
            return True
        return False

    def reset(self):
        self.config['role'] = self.roles[0]
        self.config['grupo'] = 0
        for k in self.config.keys():
            if k not in ['role', 'grupo']:
                self.config[k] = None

    def display_config(self, display_module, delay_ms=500):
        from microbit import sleep
        display_module.show(str(self.config['role']))
        sleep(delay_ms)
        display_module.show(str(self.config['grupo']))
        sleep(delay_ms)
        display_module.clear()

    def get_all(self):
        return dict(self.config)
