# socketio_manager.py - Cliente Socket.IO hacia ClassQuiz
# VERSIÓN CORREGIDA - Basado en proxy.py funcional

import socketio
import time
from threading import Thread

# ============================================================================
# VARIABLES GLOBALES (como proxy.py)
# ============================================================================
pregunta_actual = None
tipo_pregunta_actual = None
num_opciones_actual = 4
opciones_actuales = []

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def conectar_dispositivo(device_id, info, url, pin, estado):
    """
    Conecta un dispositivo a ClassQuiz.
    Basado en el flujo de proxy.py
    """
    nombre = info['nombre']
    
    print(f"[Socket.IO] Conectando {nombre}...")
    
    # Crear cliente
    cliente = socketio.Client(
        reconnection=True,
        reconnection_attempts=5,
        reconnection_delay=1,
        reconnection_delay_max=5
    )
    
    # Configurar eventos
    configurar_cliente_socketio(cliente, nombre, device_id, pin, estado)
    
    # Guardar cliente en estado ANTES de conectar
    estado['dispositivos'][device_id]['cliente'] = cliente
    estado['dispositivos'][device_id]['conectado'] = False
    
    try:
        # Conectar
        cliente.connect(url, transports=['websocket', 'polling'])
        
        # Esperar 2 segundos (como proxy.py)
        time.sleep(2.0)
        
        # Verificar si recibió joined_game
        if not estado['dispositivos'][device_id].get('conectado'):
            print(f"[Socket.IO] ⚠️ {nombre} - No recibió joined_game")
        
    except Exception as e:
        print(f"[Socket.IO] ❌ Error conectando {nombre}: {e}")


def configurar_cliente_socketio(cliente, nombre, device_id, pin, estado):
    """
    Configura eventos Socket.IO (EXACTO de proxy.py)
    """
    
    @cliente.event
    def connect():
        print(f"[Socket.IO] {nombre} conectado")
        cliente.emit('join_game', {
            'username': nombre,
            'game_pin': pin,
            'captcha': None,
            'custom_field': None
        })
    
    @cliente.event
    def disconnect():
        print(f"[Socket.IO] {nombre} desconectado")
        if device_id in estado['dispositivos']:
            estado['dispositivos'][device_id]['conectado'] = False
    
    @cliente.on('joined_game')
    def on_joined_game(data):
        print(f"[ClassQuiz] {nombre} unido ✓")
        estado['dispositivos'][device_id]['conectado'] = True
        estado['dispositivos'][device_id]['estado'] = 'online'
    
    @cliente.on('start_game')
    def on_start_game():
        print(f"[ClassQuiz] Juego iniciado")
    
    @cliente.on('time_sync')
    def on_time_sync(data):
        cliente.emit('echo_time_sync', data)
    
    @cliente.on('set_question_number')
    def on_set_question(data):
        # Solo primer dispositivo procesa
        if list(estado['dispositivos'].keys())[0] == device_id:
            print(f"[ClassQuiz] Pregunta recibida")
            procesar_nueva_pregunta(data, estado)
    
    @cliente.on('question_results')
    def on_results(data):
        pass
    
    @cliente.on('final_results')
    def on_final(data):
        print(f"[ClassQuiz] Juego finalizado")
    
    @cliente.on('error')
    def on_error(data):
        print(f"[Socket.IO] Error {nombre}: {data}")


def procesar_nueva_pregunta(data, estado):
    """
    Procesa pregunta de ClassQuiz (con timeout inteligente)
    """
    global pregunta_actual, tipo_pregunta_actual, num_opciones_actual, opciones_actuales
    
    pregunta_actual = data.get('question_index', 0)
    question = data.get('question', {})
    
    question_type = question.get('type', 'ABCD')
    tipo_pregunta_actual = "multiple" if question_type != 'ABCD' else "unica"
    
    answers = question.get('answers', [])
    opciones_actuales = [ans.get('answer', '') for ans in answers]
    num_opciones_actual = len(opciones_actuales)
    
    if num_opciones_actual < 2:
        num_opciones_actual = 4
        opciones_actuales = ['A', 'B', 'C', 'D']
    
    print(f"[ClassQuiz] Pregunta {pregunta_actual}: {tipo_pregunta_actual}, {num_opciones_actual} opciones")
    print(f"[ClassQuiz] Opciones: {opciones_actuales}")
    
    # Enviar a concentrador
    import serial_manager
    serial_manager.enviar({
        'type': 'question_params',
        'q_type': tipo_pregunta_actual,
        'num_options': num_opciones_actual
    })
    
    # Calcular timeout inteligente
    tiempo_classquiz = int(question.get('time', 30))
    tiempo_classquiz_menos_lag = max(3, tiempo_classquiz - 2)
    timeout_configurado = estado.get('timeout_votacion', 0)
    
    # Aplicar lógica de selección
    if timeout_configurado == 0:
        # Modo automático
        timeout = tiempo_classquiz_menos_lag
        print(f"[Timeout] Automático: {timeout}s (ClassQuiz: {tiempo_classquiz}s - 2s lag)")
    elif timeout_configurado > tiempo_classquiz_menos_lag:
        # Configurado excede límite
        timeout = tiempo_classquiz_menos_lag
        print(f"[Timeout] Límite: {timeout}s (configurado {timeout_configurado}s > máx {tiempo_classquiz_menos_lag}s)")
    else:
        # Valor manual válido (1 <= timeout <= tiempo_classquiz_menos_lag)
        timeout = timeout_configurado
        print(f"[Timeout] Manual: {timeout}s (máx permitido: {tiempo_classquiz_menos_lag}s)")
    
    # Iniciar countdown automático en thread separado
    def countdown_votacion():
        print(f"[Votacion] Esperando {timeout}s...")
        for i in range(timeout, 0, -1):
            print(f"[Votacion] {i}...")
            time.sleep(1)
        
        print("[Votacion] Iniciando polling...")
        serial_manager.enviar({"type": "start_poll"})
    
    # Ejecutar countdown en background
    Thread(target=countdown_votacion, daemon=True).start()


def enviar_respuesta(device_id, answer_letra, estado):
    """
    Envía respuesta a ClassQuiz (EXACTO de proxy.py)
    """
    print(f"[Socket.IO] enviar_respuesta: {device_id[:8]} → '{answer_letra}'")
    
    if device_id not in estado['dispositivos']:
        print(f"[Socket.IO] ❌ Dispositivo no encontrado")
        return
    
    info = estado['dispositivos'][device_id]
    cliente = info.get('cliente')
    nombre = info.get('nombre', device_id[:8])
    
    if not cliente:
        print(f"[Socket.IO] ❌ Sin cliente para {nombre}")
        return
    
    if not info.get('conectado'):
        print(f"[Socket.IO] ⚠️ {nombre} no conectado")
        return
    
    # Mapear A/B/C/D → texto
    if answer_letra in ['A', 'B', 'C', 'D']:
        indice = ord(answer_letra) - ord('A')
        
        if 0 <= indice < len(opciones_actuales):
            answer_text = opciones_actuales[indice]
            print(f"[Mapeo] {nombre}: {answer_letra} → '{answer_text}'")
        else:
            print(f"[Socket.IO] ❌ Índice fuera de rango")
            return
    elif answer_letra == "":
        answer_text = ""
        print(f"[Respuesta] {nombre}: (sin respuesta)")
    else:
        answer_text = answer_letra
        print(f"[Respuesta] {nombre}: {answer_text}")
    
    # Enviar a ClassQuiz
    try:
        cliente.emit('submit_answer', {
            'question_index': pregunta_actual,
            'answer': answer_text
        })
        print(f"[→ClassQuiz] {nombre}: ✓")
    except Exception as e:
        print(f"[Socket.IO] ❌ Error enviando: {e}")


def conectar_todos(estado):
    """
    Conecta todos los dispositivos a ClassQuiz
    """
    print("[Socket.IO] Iniciando conectar_todos...")
    
    dispositivos_a_conectar = []
    
    # Recopilar dispositivos sin cliente
    for device_id, info in estado['dispositivos'].items():
        if not info.get('cliente'):
            dispositivos_a_conectar.append((device_id, info))
            print(f"[Socket.IO] Agregado: {info.get('nombre', device_id[:8])}")
    
    print(f"[Socket.IO] Total a conectar: {len(dispositivos_a_conectar)}")
    
    # Conectar cada uno en thread separado
    for idx, (device_id, info) in enumerate(dispositivos_a_conectar, 1):
        print(f"[Socket.IO] Iniciando thread {idx}/{len(dispositivos_a_conectar)}")
        
        thread = Thread(
            target=conectar_dispositivo,
            args=(
                device_id,
                info,
                estado['url_classquiz'],
                estado['game_pin'],
                estado
            ),
            daemon=True
        )
        thread.start()
        time.sleep(0.5)
    
    print(f"[Socket.IO] Threads iniciados ({len(dispositivos_a_conectar)} dispositivos)")


def desconectar_todos(estado):
    """
    Desconecta todos los clientes Socket.IO
    """
    print("[Socket.IO] Desconectando todos los clientes...")
    
    for device_id, info in list(estado['dispositivos'].items()):
        cliente = info.get('cliente')
        
        if cliente:
            try:
                cliente.disconnect()
                print(f"[Socket.IO] Cliente {device_id[:8]} desconectado")
            except Exception as e:
                print(f"[Socket.IO] Error desconectando {device_id[:8]}: {e}")
        
        # Limpiar estado
        info['cliente'] = None
        info['conectado'] = False
        if 'estado' in info:
            info['estado'] = 'registrado'
    
    print("[Socket.IO] Todos los clientes desconectados")


def obtener_estado_clientes(estado):
    """
    Obtiene estado de todos los clientes
    """
    resultado = {}
    
    for device_id, info in estado['dispositivos'].items():
        cliente = info.get('cliente')
        
        if cliente:
            try:
                resultado[device_id] = {
                    'conectado': cliente.connected,
                    'transporte': 'websocket' if cliente.connected else 'disconnected'
                }
            except:
                resultado[device_id] = {
                    'conectado': False,
                    'transporte': 'error'
                }
        else:
            resultado[device_id] = {
                'conectado': False,
                'transporte': 'sin_cliente'
            }
    
    return resultado