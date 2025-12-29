# proxy.py
# Proxy USB-Concentrador <-> ClassQuiz Socket.IO
# Adaptado para sistema grupo:rol

import serial
import socketio
import json
import time
import threading
import sys
from random import choice

# ============================================================================
# CONFIGURACION
# ============================================================================
PUERTO_SERIE = 'COM4'
BAUDRATE = 115200
SERVIDOR_CLASSQUIZ = 'http://localhost:8000'
GAME_PIN = '610019'

NOMBRES_RANDOM = [
    "Luna", "Sol", "Estrella", "Cometa", "Nebulosa",
    "Galaxia", "Pulsar", "Quasar", "Asteroid", "Meteor",
    "Planeta", "Satelite", "Orbita", "Eclipse", "Aurora",
    "Cosmo", "Universo", "Vortex", "Quantum", "Photon"
]

# ============================================================================
# ESTADO GLOBAL
# ============================================================================
dispositivos = {}  # {device_id: {nombre, cliente, grupo, role, conectado}}
dispositivos_por_grupo_rol = {}  # {(grupo, rol): device_id}

pregunta_actual = None
tipo_pregunta_actual = None
num_opciones_actual = 4
opciones_actuales = []

puerto_serial = None
lock_serial = threading.Lock()

# ============================================================================
# FUNCIONES USB
# ============================================================================

def conectar_serial():
    global puerto_serial
    try:
        puerto_serial = serial.Serial(PUERTO_SERIE, BAUDRATE, timeout=1)
        print(f"[USB] Conectado a {PUERTO_SERIE}")
        return True
    except Exception as e:
        print(f"[USB] Error conectando: {e}")
        return False


def enviar_usb(data):
    with lock_serial:
        try:
            mensaje = json.dumps(data) + '\n'
            puerto_serial.write(mensaje.encode('utf-8'))
            print(f"[USB→Conc] {data}")
        except Exception as e:
            print(f"[USB] Error enviando: {e}")


def leer_usb_loop():
    print("[USB] Thread de lectura iniciado")
    
    while True:
        try:
            if puerto_serial and puerto_serial.in_waiting:
                linea = puerto_serial.readline().decode('utf-8').strip()
                
                if linea:
                    print(f"[USB←Conc] {linea}")
                    procesar_mensaje_usb(linea)
        except Exception as e:
            print(f"[USB] Error leyendo: {e}")
            time.sleep(1)
        
        time.sleep(0.05)


def procesar_mensaje_usb(linea):
    try:
        data = json.loads(linea)
        tipo = data.get('type')
        
        print(f"[USB] Tipo: '{tipo}'")
        
        if tipo == 'debug':
            print(f"[Debug-Conc] {data.get('msg')}")
        
        elif tipo == 'new_device':
            device_id = data.get('device_id')
            grupo = data.get('grupo')
            role = data.get('role')
            print(f"[Descubrimiento] {role} G{grupo}: {device_id[:8]}")
            
            dispositivos[device_id] = {
                'pendiente': True,
                'grupo': grupo,
                'role': role
            }
            dispositivos_por_grupo_rol[(grupo, role)] = device_id
        
        elif tipo == 'discovery_end':
            total = data.get('total', 0)
            print(f"\n[Descubrimiento] Completo: {total} dispositivos")
            
            ids_pendientes = [d for d in dispositivos.keys() if dispositivos[d].get('pendiente')]
            if ids_pendientes:
                registrar_dispositivos(ids_pendientes)
            else:
                print("[Warning] No hay dispositivos pendientes")
        
        elif tipo == 'answer':
            device_id = data.get('device_id')
            grupo = data.get('grupo', 0)
            role = data.get('role', '?')
            answer = data.get('answer')
            print(f"[ANSWER] G{grupo}:{role} ({device_id[:8]}) → '{answer}'")
            procesar_respuesta(device_id, answer)
        
        elif tipo == 'polling_complete':
            print("[Polling] Completo")
        
        elif tipo == 'error':
            print(f"[Error-Conc] {data.get('msg')}")
        
        else:
            print(f"[USB] Mensaje no reconocido: {data}")
    
    except json.JSONDecodeError as e:
        print(f"[USB] JSON invalido: {linea}")
        print(f"[USB] Error: {e}")
    except Exception as e:
        print(f"[USB] Error procesando: {e}")


# ============================================================================
# GESTION DE DISPOSITIVOS
# ============================================================================

def registrar_dispositivos(lista_ids):
    global dispositivos
    
    print(f"\n[Registro] {len(lista_ids)} dispositivos")
    
    for device_id in lista_ids:
        info = dispositivos.get(device_id, {})
        role = info.get('role', 'X')
        grupo = info.get('grupo', 0)
        
        nombre = f"{choice(NOMBRES_RANDOM)}_{role}G{grupo}"
        
        cliente = socketio.Client()
        configurar_cliente_socketio(cliente, nombre, device_id)
        
        dispositivos[device_id] = {
            "nombre": nombre,
            "cliente": cliente,
            "conectado": False,
            "role": role,
            "grupo": grupo,
            "pendiente": False
        }
        
        threading.Thread(
            target=conectar_cliente,
            args=(device_id,),
            daemon=True
        ).start()
    
    print(f"[Registro] Total: {len(dispositivos)} estudiantes")


def conectar_cliente(device_id):
    info = dispositivos[device_id]
    cliente = info['cliente']
    nombre = info['nombre']
    
    try:
        print(f"[Socket.IO] Conectando {nombre}...")
        cliente.connect(SERVIDOR_CLASSQUIZ)
        time.sleep(2.0)
        
        if not info.get('conectado'):
            print(f"[⚠️] {nombre} - No recibio joined_game")
    
    except Exception as e:
        print(f"[Socket.IO] Error {nombre}: {e}")


# ============================================================================
# SOCKET.IO - EVENTOS CLASSQUIZ
# ============================================================================

def configurar_cliente_socketio(cliente, nombre, device_id):
    
    @cliente.event
    def connect():
        print(f"[Socket.IO] {nombre} conectado")
        cliente.emit('join_game', {
            'username': nombre,
            'game_pin': GAME_PIN,
            'captcha': None,
            'custom_field': None
        })
    
    @cliente.event
    def disconnect():
        print(f"[Socket.IO] {nombre} desconectado")
        dispositivos[device_id]['conectado'] = False
    
    @cliente.on('joined_game')
    def on_joined_game(data):
        print(f"[ClassQuiz] {nombre} unido ✓")
        dispositivos[device_id]['conectado'] = True
    
    @cliente.on('start_game')
    def on_start_game():
        print(f"[ClassQuiz] Juego iniciado")
    
    @cliente.on('time_sync')
    def on_time_sync(data):
        cliente.emit('echo_time_sync', data)
    
    @cliente.on('set_question_number')
    def on_set_question(data):
        if list(dispositivos.keys())[0] == device_id:
            print(f"[ClassQuiz] Pregunta recibida")
            procesar_nueva_pregunta(data)
    
    @cliente.on('question_results')
    def on_results(data):
        pass
    
    @cliente.on('final_results')
    def on_final(data):
        print(f"[ClassQuiz] Juego finalizado")
    
    @cliente.on('error')
    def on_error(data):
        print(f"[Socket.IO] Error {nombre}: {data}")


def procesar_nueva_pregunta(data):
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
    
    print(f"\n[ClassQuiz] Pregunta {pregunta_actual}: {tipo_pregunta_actual}, {num_opciones_actual} opciones")
    print(f"[ClassQuiz] Opciones: {opciones_actuales}")
    
    msg = {
        "type": "question_params",
        "q_type": tipo_pregunta_actual,
        "num_options": num_opciones_actual
    }
    enviar_usb(msg)
    
    print("[Votacion] Esperando 10s...")
    for i in range(10, 0, -1):
        print(f"[Votacion] {i}...")
        time.sleep(1)
    
    enviar_usb({"type": "start_poll"})


def procesar_respuesta(device_id, answer):
    if device_id not in dispositivos:
        print(f"[Warning] Dispositivo desconocido: {device_id}")
        return
    
    info = dispositivos[device_id]
    cliente = info['cliente']
    nombre = info['nombre']
    
    if not info['conectado']:
        print(f"[Warning] {nombre} no conectado")
        return
    
    if answer in ['A', 'B', 'C', 'D']:
        indice = ord(answer) - ord('A')
        
        if 0 <= indice < len(opciones_actuales):
            answer_text = opciones_actuales[indice]
            print(f"[Mapeo] {nombre}: {answer} → '{answer_text}'")
        else:
            print(f"[Error] {nombre}: Indice fuera de rango")
            return
    elif answer == "":
        answer_text = ""
        print(f"[Respuesta] {nombre}: (sin respuesta)")
    else:
        answer_text = answer
        print(f"[Respuesta] {nombre}: {answer_text}")
    
    try:
        cliente.emit('submit_answer', {
            'question_index': pregunta_actual,
            'answer': answer_text
        })
        print(f"[→ClassQuiz] {nombre}: ✓")
    except Exception as e:
        print(f"[Error] {nombre}: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("PROXY MICROBIT-CLASSQUIZ (GRUPO:ROL)")
    print("=" * 80)
    print(f"Servidor: {SERVIDOR_CLASSQUIZ}")
    print(f"Game PIN: {GAME_PIN}")
    print(f"Puerto: {PUERTO_SERIE}")
    print("=" * 80)
    
    if not conectar_serial():
        print("[Error] No se pudo conectar")
        sys.exit(1)
    
    thread_usb = threading.Thread(target=leer_usb_loop, daemon=True)
    thread_usb.start()
    
    print("\n[Esperando] Boton A en concentrador para descubrir")
    print("[Ctrl+C para salir]\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Saliendo]...")
        for info in dispositivos.values():
            try:
                info['cliente'].disconnect()
            except:
                pass
        print("[OK] Salida limpia")


if __name__ == '__main__':
    main()