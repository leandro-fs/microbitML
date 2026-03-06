# apps/classquiz/app.py
import csv
import time
from threading import Lock, Thread
from flask import Blueprint, render_template, request, jsonify
from flask_socketio import emit
from core.base_app import BaseApp
from core.server import socketio
from core import serial_manager, utils

# Defaults propios de classquiz
DEFAULT_URL     = 'http://localhost:8000'
DEFAULT_PIN     = '000000'
DEFAULT_TIMEOUT = 0
CONFIG_FILE     = 'data/classquiz_config.csv'
ALUMNOS_FILE    = 'data/alumnos.csv'

class ClassquizApp(BaseApp):
    id    = "classquiz"
    label = "🌐 ClassQuiz"

    def __init__(self):
        self.estado = {
            'url': DEFAULT_URL,
            'pin': DEFAULT_PIN,
            'timeout': DEFAULT_TIMEOUT,
            'dispositivos': {},
        }
        self.lock = Lock()
        # importar aqui para evitar circular
        from apps.classquiz import socketio_manager as sm
        self.sm = sm

    def get_blueprint(self):
        bp = Blueprint('classquiz', __name__,
                       template_folder='templates',
                       static_folder='static',
                       url_prefix='/classquiz')

        @bp.route('/')
        def index():
            return render_template('classquiz/index.html')

        @bp.route('/api/config', methods=['GET'])
        def get_config():
            with self.lock:
                return jsonify(self.estado)

        @bp.route('/api/config', methods=['POST'])
        def set_config():
            data = request.json
            with self.lock:
                self.estado['url']     = data.get('url', self.estado['url'])
                self.estado['pin']     = data.get('pin', self.estado['pin'])
                self.estado['timeout'] = int(data.get('timeout', self.estado['timeout']))
            self._guardar_config()
            socketio.emit('log', {'nivel': 'INFO', 'msg': 'Config guardada',
                                  'timestamp': utils.timestamp()})
            return jsonify({'status': 'ok'})

        @bp.route('/api/descubrir', methods=['POST'])
        def descubrir():
            self._iniciar_descubrimiento()
            return jsonify({'status': 'ok'})

        @bp.route('/api/cargar_config', methods=['POST'])
        def cargar_config():
            from flask import request as req
            file = req.files.get('file')
            if not file:
                return jsonify({'error': 'No se recibió archivo'}), 400
            try:
                import io
                content      = file.read().decode('utf-8')
                reader       = csv.DictReader(io.StringIO(content))
                config_data  = {}
                alumnos      = []
                for row in reader:
                    # Primera fila puede ser config o alumno según columnas
                    if 'url' in row and not config_data:
                        config_data = row
                    if 'device_id' in row and row.get('device_id'):
                        alumnos.append({
                            'id':     row.get('device_id', ''),
                            'nombre': row.get('nombre_alumno', row.get('nombre', '')),
                            'grp':    row.get('grupo', ''),
                            'rol':    row.get('role', row.get('rol', '')),
                            'estado': 'registrado'
                        })
                with self.lock:
                    if config_data.get('url'):
                        self.estado['url'] = config_data['url']
                    if config_data.get('pin') or config_data.get('game_pin'):
                        self.estado['pin'] = config_data.get('pin') or config_data.get('game_pin')
                    if config_data.get('timeout') or config_data.get('timeout_votacion'):
                        self.estado['timeout'] = int(config_data.get('timeout') or config_data.get('timeout_votacion', 0))
                    for a in alumnos:
                        if a['id']:
                            self.estado['dispositivos'][a['id']] = {
                                'device_id': a['id'], 'nombre': a['nombre'],
                                'grp': a['grp'], 'rol': a['rol'],
                                'estado': 'registrado', 'cliente': None, 'conectado': False
                            }
                socketio.emit('config_cargada', {
                    'url': self.estado['url'], 'pin': self.estado['pin'],
                    'timeout': self.estado['timeout'], 'alumnos': alumnos
                })
                return jsonify({'status': 'ok', 'alumnos_cargados': len(alumnos),
                                'url': self.estado['url'], 'pin': self.estado['pin'],
                                'timeout': self.estado['timeout']})
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @bp.route('/api/guardar_todo', methods=['POST'])
        def guardar_todo():
            from flask import request as req, make_response
            import io as io_module
            data         = req.json
            nombre_arch  = data.get('nombre_archivo', 'config')
            alumnos      = data.get('alumnos', [])
            url          = data.get('url', self.estado['url'])
            pin          = data.get('pin', self.estado['pin'])
            timeout      = data.get('timeout', self.estado['timeout'])

            output = io_module.StringIO()
            # Primera fila: config
            w = csv.writer(output)
            w.writerow(['url', 'game_pin', 'timeout_votacion'])
            w.writerow([url, pin, timeout])
            w.writerow([])
            # Filas de alumnos
            w.writerow(['device_id', 'nombre_alumno', 'grupo', 'role'])
            for a in alumnos:
                w.writerow([a.get('id',''), a.get('nombre',''), a.get('grupo',''), a.get('role','')])

            csv_content = output.getvalue()
            response    = make_response(csv_content)
            response.headers['Content-Type']        = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename={nombre_arch}.csv'
            return response

        @bp.route('/api/conectar', methods=['POST'])
        def conectar():
            data    = request.get_json(silent=True) or {}
            url     = data.get('url', '').strip()
            pin     = data.get('pin', '').strip()
            timeout = data.get('timeout')
            if url:
                self.estado['url'] = url
            if pin:
                self.estado['pin'] = pin
            if timeout is not None:
                try:
                    self.estado['timeout'] = int(timeout)
                except ValueError:
                    pass
            with self.lock:
                num = len(self.estado['dispositivos'])
            if num == 0:
                return jsonify({'error': 'No hay dispositivos. Ejecuta descubrimiento primero.'}), 400
            print(f"[ClassQuiz] Conectando → url={self.estado['url']} pin={self.estado['pin']} dispositivos={num}")
            self._conectar_classquiz()
            return jsonify({'status': 'ok'})

        @bp.route('/api/dispositivos', methods=['GET'])
        def dispositivos():
            with self.lock:
                return jsonify({'dispositivos': list(self.estado['dispositivos'].values())})

        @bp.route('/api/alumnos', methods=['POST'])
        def guardar_alumnos():
            data = request.json
            self._guardar_alumnos(data.get('alumnos', []))
            return jsonify({'status': 'ok'})

        @bp.route('/api/renombrar', methods=['POST'])
        def renombrar():
            data      = request.json
            device_id = data.get('device_id')
            nombre    = data.get('nombre', '').strip()
            if not device_id or not nombre:
                return jsonify({'error': 'device_id y nombre requeridos'}), 400
            with self.lock:
                if device_id not in self.estado['dispositivos']:
                    return jsonify({'error': 'Dispositivo no encontrado'}), 404
                self.estado['dispositivos'][device_id]['nombre'] = nombre
            print(f"[ClassQuiz] Renombrar {device_id[:8]} → '{nombre}'")
            return jsonify({'status': 'ok'})

        return bp

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def on_start(self):
        self._cargar_config()
        print("[ClassQuiz] Iniciado")

    def on_stop(self):
        self.sm.desconectar_todos(self.estado)
        print("[ClassQuiz] Detenido")

    def on_message(self, msg: dict):
        name  = msg.get('name')
        event = msg.get('event')

        if event == 'gateway_ready':
            socketio.emit('log', {'nivel': 'INFO', 'msg': 'Gateway listo',
                                  'timestamp': utils.timestamp()})
        elif event == 'button_a':
            self._iniciar_descubrimiento()
        elif event == 'button_b':
            self._verificar_estado()
        elif name == 'ID':
            self._procesar_id(msg)
        elif name == 'ANSWER':
            self._procesar_answer(msg)
        elif name == 'PONG':
            self._procesar_pong(msg)
        elif name == 'CHECK_REG':
            self._procesar_check_reg(msg)

    # ------------------------------------------------------------------
    # Lógica de negocio
    # ------------------------------------------------------------------

    def _iniciar_descubrimiento(self):
        with self.lock:
            self.estado['dispositivos'].clear()
        socketio.emit('log', {'nivel': 'INFO', 'msg': 'Descubrimiento iniciado',
                              'timestamp': utils.timestamp()})
        serial_manager.enviar({'name': 'REPORT', 'grp': 0, 'rol': 'est', 'valores': []})

        def esperar_ids():
            time.sleep(10)
            with self.lock:
                total = len(self.estado['dispositivos'])
            socketio.emit('discovery_end', {'total': total})
            socketio.emit('log', {'nivel': 'INFO',
                                  'msg': f'Descubrimiento completo: {total} dispositivos',
                                  'timestamp': utils.timestamp()})

        Thread(target=esperar_ids, daemon=True).start()

    def _procesar_id(self, msg):
        device_id = msg.get('devID')
        grp       = msg.get('grp')
        rol       = msg.get('rol')
        clave     = (grp, rol)

        with self.lock:
            if clave in {(v['grp'], v['rol']) for v in self.estado['dispositivos'].values()}:
                socketio.emit('log', {'nivel': 'WARNING',
                                      'msg': f'Conflicto G{grp}:{rol}',
                                      'timestamp': utils.timestamp()})
            self.estado['dispositivos'][device_id] = {
                'device_id': device_id, 'grp': grp, 'rol': rol,
                'nombre': device_id[:8], 'estado': 'registrado',
                'cliente': None, 'conectado': False
            }

        serial_manager.enviar({'name': 'ACK', 'devID': device_id,
                                'grp': grp, 'rol': rol, 'valores': []})
        socketio.emit('new_device', {'device_id': device_id, 'grp': grp, 'rol': rol,
                                     'timestamp': utils.timestamp()})

    def _procesar_answer(self, msg):
        device_id = msg.get('devID')
        respuesta = msg.get('valores', [])
        with self.lock:
            info = self.estado['dispositivos'].get(device_id, {})
        nombre = info.get('nombre', device_id[:8] if device_id else '?')
        socketio.emit('respuesta_recibida', {'device_id': device_id,
                                             'nombre': nombre, 'respuesta': respuesta,
                                             'timestamp': utils.timestamp()})
        self.sm.enviar_respuesta(device_id, respuesta, self.estado)

    def _procesar_pong(self, msg):
        device_id = msg.get('devID')
        with self.lock:
            if device_id in self.estado['dispositivos']:
                self.estado['dispositivos'][device_id]['estado'] = 'online'
        socketio.emit('ping_result', {'device_id': device_id, 'status': 'online',
                                      'timestamp': utils.timestamp()})

    def _procesar_check_reg(self, msg):
        device_id = msg.get('devID')
        grp       = msg.get('grp')
        rol       = msg.get('rol')
        with self.lock:
            match = next((v for v in self.estado['dispositivos'].values()
                          if v['grp'] == grp and v['rol'] == rol), None)
        if match:
            estado_reg = 'OK' if match['device_id'] == device_id else 'CONFLICT'
        else:
            estado_reg = 'NO'
        serial_manager.enviar({'name': 'REG_STATUS', 'devID': device_id,
                                'grp': grp, 'rol': rol, 'valores': [estado_reg]})

    def _verificar_estado(self):
        with self.lock:
            dispositivos = list(self.estado['dispositivos'].items())
        for device_id, info in dispositivos:
            serial_manager.enviar({'name': 'PING', 'devID': device_id,
                                   'grp': info['grp'], 'rol': info['rol'], 'valores': []})

    def _conectar_classquiz(self):
        self.sm.desconectar_todos(self.estado)
        self.sm.conectar_todos(self.estado)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _guardar_config(self):
        utils.crear_directorio_data()
        with open(CONFIG_FILE, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['url', 'pin', 'timeout'])
            w.writeheader()
            with self.lock:
                w.writerow({'url': self.estado['url'],
                            'pin': self.estado['pin'],
                            'timeout': self.estado['timeout']})

    def _cargar_config(self):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                row = next(csv.DictReader(f))
                with self.lock:
                    self.estado['url']     = row.get('url', DEFAULT_URL)
                    self.estado['pin']     = row.get('pin', DEFAULT_PIN)
                    self.estado['timeout'] = int(row.get('timeout', DEFAULT_TIMEOUT))
        except FileNotFoundError:
            pass

    def _guardar_alumnos(self, alumnos):
        utils.crear_directorio_data()
        with open(ALUMNOS_FILE, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['device_id', 'nombre', 'grp', 'rol'])
            w.writeheader()
            for a in alumnos:
                w.writerow(a)