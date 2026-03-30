# apps/classquiz/socketio_manager.py
import socketio as sio_client
import time
from threading import Thread, Event

ACTIVITY = 'cqz'

_pregunta_actual   = None
_opciones_actuales = []

# device_id -> Event, señalizado cuando llega el ANSWER durante el polling
_eventos_respuesta = {}

def notify_answer(device_id):
    """Llamado por app.py cuando llega un ANSWER durante el polling activo."""
    if device_id in _eventos_respuesta:
        _eventos_respuesta[device_id].set()


def conectar_dispositivo(device_id, info, url, pin, estado):
    nombre  = info.get('nombre', device_id[:8])
    print(f"[SocketIO] Conectando '{nombre}' → {url} (PIN:{pin})")
    cliente = sio_client.Client(
        reconnection=True,
        reconnection_attempts=5,
        reconnection_delay=1,
        reconnection_delay_max=5
    )

    @cliente.event
    def connect():
        print(f"[SocketIO] {nombre} conectado al servidor, enviando join_game...")
        cliente.emit('join_game', {'username': nombre, 'game_pin': pin,
                                   'captcha': None, 'custom_field': None})

    @cliente.event
    def disconnect():
        print(f"[SocketIO] {nombre} desconectado")
        if device_id in estado['dispositivos']:
            estado['dispositivos'][device_id]['conectado'] = False

    @cliente.on('joined_game')
    def on_joined(data):
        print(f"[SocketIO] {nombre} unido al juego OK")
        estado['dispositivos'][device_id]['conectado'] = True
        estado['dispositivos'][device_id]['estado']    = 'online'

    @cliente.on('set_question_number')
    def on_pregunta(data):
        global _pregunta_actual, _opciones_actuales
        # Solo el primer dispositivo dispara el envio por serial
        if list(estado['dispositivos'].keys())[0] != device_id:
            return

        _pregunta_actual   = data.get('question_index', 0)
        answers            = data.get('question', {}).get('answers', [])
        _opciones_actuales = [a.get('answer', '') for a in answers] or ['A', 'B', 'C', 'D']
        num_opciones       = len(_opciones_actuales)
        tipo               = 'multiple' if data.get('question', {}).get('multiple_select') else 'unica'
        tiempo_classquiz   = int(data.get('question', {}).get('time', 30))

        print(f"[SocketIO] Pregunta {_pregunta_actual} ({tipo}, {num_opciones} opciones): {_opciones_actuales}")

        from core import serial_manager, utils
        from core.server import socketio

        serial_manager.enviar({
            'name': 'QPARAMS',
            'act': ACTIVITY,
            'grp': 0,
            'rol': 'est',
            'valores': [tipo, str(num_opciones)]
        })
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f'Pregunta {_pregunta_actual}: {tipo}, {num_opciones} opciones',
            'timestamp': utils.timestamp()
        })

        # Timeout: 2s menos que ClassQuiz para asegurar que las respuestas lleguen antes
        timeout_configurado = estado.get('timeout', 0)
        tiempo_max          = max(3, tiempo_classquiz - 2)
        if timeout_configurado == 0 or timeout_configurado > tiempo_max:
            timeout = tiempo_max
        else:
            timeout = timeout_configurado

        def countdown_y_poll():
            print(f"[Votacion] Esperando {timeout}s...")
            socketio.emit('votacion_iniciada', {'timeout': timeout, 'timestamp': utils.timestamp()})
            for i in range(timeout, 0, -1):
                socketio.emit('countdown', {'segundos': i})
                time.sleep(1)
            _hacer_polling(estado)

        Thread(target=countdown_y_poll, daemon=True).start()

    @cliente.on('time_sync')
    def on_time_sync(data):
        cliente.emit('echo_time_sync', data)

    @cliente.on('error')
    def on_error(data):
        print(f"[SocketIO] Error servidor para {nombre}: {data}")

    estado['dispositivos'][device_id]['cliente'] = cliente

    try:
        cliente.connect(url, transports=['websocket', 'polling'])
        time.sleep(2)
        if not estado['dispositivos'][device_id].get('conectado'):
            print(f"[SocketIO] AVISO: {nombre} conectó pero no recibió joined_game (PIN incorrecto o juego no iniciado)")
    except Exception as e:
        print(f"[SocketIO] Error conectando '{nombre}': {type(e).__name__}: {e}")
        estado['dispositivos'][device_id]['cliente'] = None


def _hacer_polling(estado):
    """
    Recorre todos los dispositivos enviando POLL por grp+rol.
    Espera activamente el ANSWER con timeout y reintento por dispositivo.
    Las respuestas llegan via notify_answer() llamado desde app.py.
    """
    from core import serial_manager, utils
    from core.server import socketio

    TIMEOUT_RESPUESTA = 0.5   # segundos de espera por respuesta
    MAX_INTENTOS      = 1

    print("[Votacion] Iniciando polling...")
    socketio.emit('log', {'nivel': 'INFO', 'msg': 'Polling iniciado',
                          'timestamp': utils.timestamp()})

    dispositivos = list(estado['dispositivos'].items())

    for device_id, info in dispositivos:
        grp    = info.get('grp')
        rol    = info.get('rol')
        nombre = info.get('nombre', device_id[:8])

        # Preparar Event para este dispositivo
        evento = Event()
        _eventos_respuesta[device_id] = evento

        respondio = False
        for intento in range(1, MAX_INTENTOS + 1):
            evento.clear()
            serial_manager.enviar({'name': 'POLL', 'act': ACTIVITY,
                                   'grp': grp, 'rol': rol, 'valores': []})
            print(f"[Votacion] POLL → {nombre} G{grp}:{rol} (intento {intento})")

            if evento.wait(timeout=TIMEOUT_RESPUESTA):
                print(f"[Votacion] ANSWER recibido de {nombre}")
                respondio = True
                break

        if not respondio:
            print(f"[Votacion] Sin respuesta de {nombre} G{grp}:{rol}")
            socketio.emit('log', {'nivel': 'WARNING',
                                  'msg': f'Sin respuesta: {nombre} (G{grp}:{rol})',
                                  'timestamp': utils.timestamp()})

        # Limpiar event
        _eventos_respuesta.pop(device_id, None)

    socketio.emit('log', {'nivel': 'INFO', 'msg': 'Polling completo',
                          'timestamp': utils.timestamp()})
    print("[Votacion] Polling completo")


def conectar_todos(estado):
    url = estado['url']
    pin = estado['pin']
    for idx, (device_id, info) in enumerate(estado['dispositivos'].items()):
        if not info.get('cliente'):
            Thread(target=conectar_dispositivo,
                   args=(device_id, info, url, pin, estado),
                   daemon=True).start()
            time.sleep(0.5)

def desconectar_todos(estado):
    for device_id, info in list(estado['dispositivos'].items()):
        cliente = info.get('cliente')
        if cliente:
            try:
                cliente.disconnect()
            except:
                pass
        info['cliente']   = None
        info['conectado'] = False

def enviar_respuesta(device_id, respuesta_lista, estado):
    global _pregunta_actual, _opciones_actuales
    info    = estado['dispositivos'].get(device_id, {})
    cliente = info.get('cliente')
    if not cliente or not info.get('conectado'):
        return

    letras = ['A', 'B', 'C', 'D']
    textos = []
    for letra in respuesta_lista:
        if letra in letras:
            idx = letras.index(letra)
            textos.append(_opciones_actuales[idx] if idx < len(_opciones_actuales) else letra)

    answer_text = textos[0] if len(textos) == 1 else ','.join(textos)

    try:
        cliente.emit('submit_answer', {
            'question_index': _pregunta_actual,
            'answer': answer_text
        })
        print(f"[SocketIO] submit_answer: {info.get('nombre', device_id[:8])} → '{answer_text}'")
    except Exception as e:
        print(f"[SocketIO] Error enviando respuesta: {e}")