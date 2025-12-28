# flask_server.py - Servidor Flask con API REST y WebSocket
# Sistema Proxy Microbit-ClassQuiz v1.2
# ACTUALIZADO: Desconexión previa + Sincronización nombres + Config dinámica

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import csv
import os
import time
from threading import Thread, Lock

import serial_manager
import socketio_manager
import config
import utils

# Crear aplicación Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Inicializar Socket.IO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading'
)

# Estado global compartido
estado = {
    'puerto_conectado': False,
    'puerto_nombre': None,
    'url_classquiz': config.DEFAULT_URL_CLASSQUIZ,
    'game_pin': config.DEFAULT_GAME_PIN,
    'timeout_votacion': config.DEFAULT_TIMEOUT,
    'dispositivos': {},  # {device_id: {nombre, grupo, role, estado, socket}}
    'pregunta_actual': None,
    'alumnos': [],
    'votacion_activa': False
}

# Lock para acceso seguro al estado
estado_lock = Lock()

# ============================================================================
# RUTAS HTTP
# ============================================================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Obtener configuración actual"""
    with estado_lock:
        return jsonify({
            'url': estado['url_classquiz'],
            'pin': estado['game_pin'],
            'puerto': estado['puerto_nombre'],
            'timeout': estado['timeout_votacion'],
            'conectado': estado['puerto_conectado']
        })


@app.route('/api/guardar_todo', methods=['POST'])
def guardar_todo():
    """Generar CSV y enviarlo como descarga"""
    try:
        data = request.json

        with estado_lock:
            # Validar datos de configuración
            url = data.get('url', estado['url_classquiz'])
            if not utils.validar_url(url):
                return jsonify({'error': 'URL inválida'}), 400

            pin = data.get('pin', estado['game_pin'])
            if not utils.validar_pin(pin):
                return jsonify({'error': 'PIN inválido'}), 400

            timeout = int(data.get('timeout', estado['timeout_votacion']))
            if timeout < 5 or timeout > 300:
                return jsonify({'error': 'Timeout debe estar entre 5 y 300 segundos'}), 400

            # Actualizar estado
            estado['url_classquiz'] = url
            estado['game_pin'] = pin
            estado['timeout_votacion'] = timeout

            # Obtener alumnos y nombre de archivo
            alumnos_data = data.get('alumnos', [])
            estado['alumnos'] = alumnos_data
            nombre_archivo = data.get('nombre_archivo', 'config_default')

        # Sanitizar nombre de archivo
        nombre_archivo = ''.join(c for c in nombre_archivo if c.isalnum() or c in ('_', '-'))

        print(f"[Flask] Generando CSV: URL={url}, PIN={pin}, Timeout={timeout}")
        print(f"[Flask] Total alumnos: {len(alumnos_data)}")

        # Generar CSV en memoria
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)

        # Sección de configuración
        writer.writerow(['[CONFIGURACION]'])
        writer.writerow(['url', url])
        writer.writerow(['game_pin', pin])
        writer.writerow(['timeout_votacion', timeout])
        writer.writerow(['puerto_serie', estado['puerto_nombre'] or ''])

        # Línea vacía como separador
        writer.writerow([])

        # Sección de alumnos
        writer.writerow(['[ALUMNOS]'])
        writer.writerow(['device_id', 'nombre_alumno', 'grupo', 'role'])

        alumnos_guardados = 0
        for alumno in alumnos_data:
            writer.writerow([
                alumno.get('id', ''),
                alumno.get('nombre', ''),
                alumno.get('grupo', ''),
                alumno.get('role', '')
            ])
            alumnos_guardados += 1

        csv_content = output.getvalue()
        output.close()

        print(f"[Flask] ✅ CSV generado: {alumnos_guardados} alumnos")

        # Notificar a clientes web
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"✅ Archivo generado: {nombre_archivo}.csv ({alumnos_guardados} alumnos)",
            'timestamp': utils.timestamp()
        })

        # Enviar como descarga
        from flask import make_response
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename={nombre_archivo}.csv'
        return response

    except Exception as e:
        print(f"[Flask] Error generando CSV: {e}")
        import traceback
        traceback.print_exc()

        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error generando archivo: {str(e)}",
            'timestamp': utils.timestamp()
        })

        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def set_config():
    """Actualizar configuración y guardar en CSV"""
    try:
        data = request.json
        
        with estado_lock:
            # Validar datos
            url = data.get('url', estado['url_classquiz'])
            if not utils.validar_url(url):
                return jsonify({'error': 'URL inválida'}), 400
            
            pin = data.get('pin', estado['game_pin'])
            if not utils.validar_pin(pin):
                return jsonify({'error': 'PIN inválido'}), 400
            
            timeout = int(data.get('timeout', estado['timeout_votacion']))
            if timeout < 5 or timeout > 300:
                return jsonify({'error': 'Timeout debe estar entre 5 y 300 segundos'}), 400
            
            # Actualizar estado
            estado['url_classquiz'] = url
            estado['game_pin'] = pin
            estado['timeout_votacion'] = timeout
        
        # Guardar en archivo
        guardar_config()
        
        # Notificar a clientes web
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Configuración actualizada correctamente',
            'timestamp': utils.timestamp()
        })

        return jsonify({'status': 'ok'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/puertos', methods=['GET'])
def listar_puertos():
    """Detectar puertos COM disponibles"""
    try:
        puertos = serial_manager.detectar_puertos()
        return jsonify({'puertos': puertos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/descubrir', methods=['POST'])
def descubrir_dispositivos():
    """Iniciar descubrimiento de micro:bits"""
    if not estado['puerto_conectado']:
        return jsonify({'error': 'Puerto no conectado'}), 400
    
    try:
        serial_manager.enviar({'type': 'start_discovery'})
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Descubrimiento de dispositivos iniciado',
            'timestamp': utils.timestamp()
        })

        return jsonify({'status': 'ok'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alumnos', methods=['GET'])
def get_alumnos():
    """Obtener lista de alumnos"""
    with estado_lock:
        return jsonify({'alumnos': estado['alumnos']})


@app.route('/api/alumnos', methods=['POST'])
def guardar_alumnos():
    """Guardar lista de alumnos en CSV"""
    try:
        data = request.json
        
        with estado_lock:
            estado['alumnos'] = data.get('alumnos', [])
        
        # Guardar en archivo
        utils.crear_directorio_data()
        
        with open(config.ALUMNOS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['device_id', 'nombre_alumno', 'grupo', 'role'])
            writer.writeheader()
            
            for alumno in estado['alumnos']:
                writer.writerow({
                    'device_id': alumno.get('id', ''),
                    'nombre_alumno': alumno.get('nombre', ''),
                    'grupo': alumno.get('grupo', ''),
                    'role': alumno.get('role', '')
                })
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"Lista de alumnos guardada ({len(estado['alumnos'])} registros)",
            'timestamp': utils.timestamp()
        })

        return jsonify({'status': 'ok'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/conectar_classquiz', methods=['POST'])
def conectar_classquiz():
    """
    Conectar todos los dispositivos detectados a ClassQuiz.
    ⭐ ACTUALIZADO: Desconecta sesión anterior primero.
    """
    try:
        # Obtener configuración desde el request
        data = request.json or {}
        
        url = data.get('url')
        pin = data.get('pin')
        timeout = data.get('timeout')
        
        # Validar parámetros
        if not url or not pin:
            error_msg = 'URL y PIN son obligatorios'
            print(f"[Flask] ❌ {error_msg}")
            socketio.emit('log', {
                'nivel': 'ERROR',
                'msg': error_msg,
                'timestamp': utils.timestamp()
            })
            return jsonify({'error': error_msg}), 400
        
        # Validar formato
        if not utils.validar_url(url):
            error_msg = f'URL inválida: {url}'
            print(f"[Flask] ❌ {error_msg}")
            socketio.emit('log', {
                'nivel': 'ERROR',
                'msg': error_msg,
                'timestamp': utils.timestamp()
            })
            return jsonify({'error': error_msg}), 400
        
        if not utils.validar_pin(pin):
            error_msg = f'PIN inválido: {pin}'
            print(f"[Flask] ❌ {error_msg}")
            socketio.emit('log', {
                'nivel': 'ERROR',
                'msg': error_msg,
                'timestamp': utils.timestamp()
            })
            return jsonify({'error': error_msg}), 400
        
        # Actualizar estado con valores recibidos
        with estado_lock:
            estado['url_classquiz'] = url
            estado['game_pin'] = pin
            if timeout:
                estado['timeout_votacion'] = int(timeout)
            
            num_dispositivos = len(estado['dispositivos'])
            dispositivos_list = list(estado['dispositivos'].items())

        print("=" * 80)
        print("[Flask] PREPARANDO CONEXIÓN A CLASSQUIZ")
        print("=" * 80)
        print(f"[Flask] URL ClassQuiz: {url}")
        print(f"[Flask] Game PIN: {pin}")
        print(f"[Flask] Timeout: {timeout}s")
        print(f"[Flask] Total dispositivos: {num_dispositivos}")
        print("=" * 80)

        if num_dispositivos == 0:
            error_msg = 'No hay dispositivos detectados. Presiona "Descubrir" primero.'
            socketio.emit('log', {
                'nivel': 'ERROR',
                'msg': error_msg,
                'timestamp': utils.timestamp()
            })
            return jsonify({'error': error_msg}), 400

        # ⭐ PASO 1: DESCONECTAR SESIÓN ANTERIOR
        print("[Flask] PASO 1/2: Desconectando sesión anterior...")
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': '🔌 Paso 1/2: Desconectando sesión anterior...',
            'timestamp': utils.timestamp()
        })
        
        desconectar_todos()
        
        # Pausa para asegurar desconexión completa
        time.sleep(0.5)
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': '✅ Sesión anterior cerrada. Iniciando nueva conexión...',
            'timestamp': utils.timestamp()
        })
        
        # ⭐ PASO 2: CONECTAR CON NUEVA CONFIGURACIÓN
        print("[Flask] PASO 2/2: Conectando con nueva configuración...")
        print("-" * 80)
        print("[Flask] LISTA DE ALUMNOS A CONECTAR:")
        for idx, (dev_id, info) in enumerate(dispositivos_list, 1):
            nombre = info.get('nombre', f'Sin nombre ({dev_id[:8]})')
            grupo = info.get('grupo', '?')
            role = info.get('role', '?')
            print(f"[Flask]   {idx}. {nombre} [G{grupo}:{role}]")
            print(f"[Flask]      Device ID: {dev_id}")
        print("=" * 80)

        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"🔗 Paso 2/2: Conectando {num_dispositivos} dispositivo(s) a {url} (PIN: {pin})...",
            'timestamp': utils.timestamp()
        })

        socketio_manager.conectar_todos(estado)

        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"✅ Conexión completada. Verifica logs para confirmar cada dispositivo.",
            'timestamp': utils.timestamp()
        })

        return jsonify({
            'status': 'ok',
            'count': num_dispositivos,
            'url': url,
            'pin': pin
        })

    except Exception as e:
        print(f"[Flask] ERROR en conectar_classquiz: {e}")
        import traceback
        traceback.print_exc()

        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error conectando: {str(e)}",
            'timestamp': utils.timestamp()
        })

        return jsonify({'error': str(e)}), 500


def desconectar_todos():
    """
    ⭐ Desconectar y limpiar sesión anterior COMPLETAMENTE.
    - Cierra todos los sockets de ClassQuiz activos
    - Limpia el estado de conexión de cada dispositivo
    - Mantiene los dispositivos detectados para reconectarlos
    """
    print("[Flask] 🧹 Limpiando sesión anterior...")
    
    with estado_lock:
        dispositivos_a_limpiar = list(estado['dispositivos'].items())
        num_dispositivos = len(dispositivos_a_limpiar)
    
    sockets_cerrados = 0
    
    # PASO 1: Cerrar todos los sockets de ClassQuiz
    for device_id, info in dispositivos_a_limpiar:
        try:
            # Cerrar socket si existe
            if 'cliente' in info and info['cliente']:
                try:
                    info['cliente'].disconnect()
                    print(f"[Flask]   ✓ Cliente cerrado: {info.get('nombre', device_id[:8])}")
                    sockets_cerrados += 1
                except Exception as e:
                    print(f"[Flask]   ✗ Error cerrando socket {device_id[:8]}: {e}")
        except Exception as e:
            print(f"[Flask] Error procesando {device_id[:8]}: {e}")
    
    # PASO 2: Limpiar estado de cada dispositivo (pero mantenerlos registrados)
    with estado_lock:
        for device_id in estado['dispositivos']:
            estado['dispositivos'][device_id]['cliente'] = None
            estado['dispositivos'][device_id]['estado'] = 'registrado'
        
        # Limpiar estado de votación
        estado['votacion_activa'] = False
        estado['pregunta_actual'] = None
        
        print(f"[Flask] ✅ Clientes cerrados: {sockets_cerrados}/{num_dispositivos}")
        print(f"[Flask] ✅ Dispositivos limpiados: {num_dispositivos}")
        print(f"[Flask] ✅ Estado reseteado - Listos para reconexión")
    
    # Notificar al frontend con dispositivos limpios
    with estado_lock:
        dispositivos_list = list(estado['dispositivos'].values())
    
    socketio.emit('dispositivos_actualizados', {
        'dispositivos': dispositivos_list
    })
    
    socketio.emit('log', {
        'nivel': 'INFO',
        'msg': f"🧹 Sesión limpiada: {sockets_cerrados} conexión(es) cerradas, {num_dispositivos} dispositivos reseteados",
        'timestamp': utils.timestamp()
    })


@app.route('/api/cargar_config', methods=['POST'])
def cargar_configuracion():
    """Cargar configuración desde archivo CSV subido"""
    try:
        # Verificar que se envió un archivo
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Solo se permiten archivos .csv'}), 400
        
        print(f"[Flask] Cargando archivo: {file.filename}")
        
        # Leer contenido del archivo
        from io import StringIO
        content = file.read().decode('utf-8')
        csv_file = StringIO(content)
        
        # Leer archivo CSV con formato especial
        config_cargada = {}
        alumnos_cargados = []
        seccion_actual = None
        
        reader = csv.reader(csv_file)
        
        for row in reader:
            if not row or len(row) == 0:
                continue
            
            # Detectar secciones
            if row[0] == '[CONFIGURACION]':
                seccion_actual = 'config'
                print(f"[Flask] Leyendo sección [CONFIGURACION]")
                continue
            elif row[0] == '[ALUMNOS]':
                seccion_actual = 'alumnos'
                print(f"[Flask] Leyendo sección [ALUMNOS]")
                continue
            
            # Procesar según sección
            if seccion_actual == 'config' and len(row) >= 2:
                key = row[0]
                value = row[1]
                config_cargada[key] = value
                print(f"[Flask]   {key}: {value}")
            
            elif seccion_actual == 'alumnos' and len(row) >= 2:
                # Saltar header
                if row[0] == 'device_id':
                    continue
                
                device_id = row[0]
                nombre = row[1]
                grupo = row[2] if len(row) > 2 else ''
                role = row[3] if len(row) > 3 else ''
                
                if device_id:
                    alumnos_cargados.append({
                        'id': device_id,
                        'nombre': nombre,
                        'grupo': grupo,
                        'role': role,
                        'estado': 'offline'
                    })
                    print(f"[Flask]   Alumno: {nombre} [G{grupo}:{role}] ({device_id[:8]})")
        
        print(f"[Flask] ✅ Config cargada: {len(config_cargada)} parámetros")
        print(f"[Flask] ✅ Alumnos cargados: {len(alumnos_cargados)}")
        
        # Actualizar estado global
        with estado_lock:
            if 'url' in config_cargada:
                estado['url_classquiz'] = config_cargada['url']
            if 'game_pin' in config_cargada:
                estado['game_pin'] = config_cargada['game_pin']
            if 'timeout_votacion' in config_cargada:
                estado['timeout_votacion'] = int(config_cargada['timeout_votacion'])
            
            estado['alumnos'] = alumnos_cargados
            
            # Actualizar dispositivos conocidos
            for alumno in alumnos_cargados:
                if alumno['id']:
                    estado['dispositivos'][alumno['id']] = {
                        'id': alumno['id'],
                        'nombre': alumno['nombre'],
                        'grupo': alumno['grupo'],
                        'role': alumno['role'],
                        'estado': 'registrado',
                        'cliente': None,
                        'conectado': False
                    }
        
        # Emitir evento de carga completa
        socketio.emit('config_cargada', {
            'url': config_cargada.get('url', ''),
            'pin': config_cargada.get('game_pin', ''),
            'timeout': config_cargada.get('timeout_votacion', 30),
            'alumnos': alumnos_cargados
        })
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': f"✅ Cargado: {file.filename} ({len(alumnos_cargados)} alumnos)",
            'timestamp': utils.timestamp()
        })
        
        return jsonify({
            'status': 'ok',
            'archivo': file.filename,
            'alumnos_cargados': len(alumnos_cargados),
            'url': config_cargada.get('url', ''),
            'pin': config_cargada.get('game_pin', ''),
            'timeout': config_cargada.get('timeout_votacion', 30)
        })
    
    except Exception as e:
        print(f"[Flask] Error cargando: {e}")
        import traceback
        traceback.print_exc()
        
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error cargando archivo: {str(e)}",
            'timestamp': utils.timestamp()
        })
        
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WEBSOCKET EVENTS (Flask-SocketIO)
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Cliente web conectado"""
    emit('log', {
        'nivel': 'INFO',
        'msg': 'Conectado al servidor proxy',
        'timestamp': utils.timestamp()
    })
    
    # Enviar estado actual
    with estado_lock:
        emit('dispositivos_actualizados', {
            'dispositivos': list(estado['dispositivos'].values())
        })


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente web desconectado"""
    print("[Flask] Cliente web desconectado")


@socketio.on('test_usb')
def handle_test_usb():
    """Test de conexión USB"""
    if not estado['puerto_conectado']:
        emit('log', {
            'nivel': 'ERROR',
            'msg': 'Puerto USB no conectado',
            'timestamp': utils.timestamp()
        })
        return
    
    try:
        serial_manager.enviar({'type': 'ping_all'})
        
        emit('log', {
            'nivel': 'INFO',
            'msg': 'Comando de test enviado al concentrador',
            'timestamp': utils.timestamp()
        })
    except Exception as e:
        emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error en test USB: {str(e)}",
            'timestamp': utils.timestamp()
        })


@socketio.on('iniciar_votacion')
def handle_iniciar_votacion():
    """Iniciar proceso de votación con countdown"""
    
    with estado_lock:
        if not estado['pregunta_actual']:
            emit('log', {
                'nivel': 'ERROR',
                'msg': 'No hay pregunta activa',
                'timestamp': utils.timestamp()
            })
            return
        
        timeout = estado['timeout_votacion']
        estado['votacion_activa'] = True
    
    # Thread para countdown
    def countdown():
        for i in range(timeout, 0, -1):
            socketio.emit('countdown', {'segundos': i})
            time.sleep(1)
        
        # Finalizar polling
        serial_manager.enviar({'type': 'start_poll'})
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Polling de respuestas iniciado',
            'timestamp': utils.timestamp()
        })
        
        with estado_lock:
            estado['votacion_activa'] = False
    
    Thread(target=countdown, daemon=True).start()


@socketio.on('finalizar_votacion')
def handle_finalizar_votacion():
    """Finalizar votación anticipadamente"""
    try:
        serial_manager.enviar({'type': 'start_poll'})
        
        with estado_lock:
            estado['votacion_activa'] = False
        
        socketio.emit('log', {
            'nivel': 'INFO',
            'msg': 'Votación finalizada manualmente',
            'timestamp': utils.timestamp()
        })
    except Exception as e:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error finalizando votación: {str(e)}",
            'timestamp': utils.timestamp()
        })


@socketio.on('actualizar_nombre')
def handle_actualizar_nombre(data):
    """Actualizar nombre de dispositivo desde frontend"""
    device_id = data.get('device_id')
    nuevo_nombre = data.get('nombre', '').strip()
    
    if not device_id or not nuevo_nombre:
        return
    
    with estado_lock:
        if device_id in estado['dispositivos']:
            nombre_anterior = estado['dispositivos'][device_id].get('nombre', '(sin nombre)')
            estado['dispositivos'][device_id]['nombre'] = nuevo_nombre
            
            grupo = estado['dispositivos'][device_id].get('grupo', '?')
            role = estado['dispositivos'][device_id].get('role', '?')
            
            print(f"[Flask] Nombre actualizado: {nombre_anterior} → {nuevo_nombre} [G{grupo}:{role}]")
            
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"✏️ Nombre actualizado: {nuevo_nombre} [G{grupo}:{role}]",
                'timestamp': utils.timestamp()
            })


# ============================================================================
# PROCESAMIENTO MENSAJES USB
# ============================================================================

def procesar_mensaje_usb(mensaje):
    """Callback desde main.py cuando llega mensaje USB"""
    try:
        data = json.loads(mensaje)
        tipo = data.get('type')
        
        socketio.emit('log', {
            'nivel': 'DEBUG',
            'msg': f"USB←Conc: {mensaje[:100]}",
            'timestamp': utils.timestamp()
        })
        
        if tipo == 'new_device':
            procesar_new_device(data)
        
        elif tipo == 'discovery_end':
            procesar_discovery_end(data)
        
        elif tipo == 'answer':
            procesar_answer(data)
        
        elif tipo == 'debug':
            socketio.emit('log', {
                'nivel': 'DEBUG',
                'msg': f"[Concentrador] {data.get('msg', '')}",
                'timestamp': utils.timestamp()
            })
        
        elif tipo == 'qparams_sent':
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"Parámetros enviados: {data.get('q_type')} - {data.get('num_options')} opciones",
                'timestamp': utils.timestamp()
            })
        
        elif tipo == 'ping_result':
            device_id = data.get('device_id', '')
            status = data.get('status', '')
            nombre = estado['dispositivos'].get(device_id, {}).get('nombre', device_id[:8])
            
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"Ping {nombre}: {status}",
                'timestamp': utils.timestamp()
            })
    
    except json.JSONDecodeError:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"JSON inválido del concentrador: {mensaje[:50]}...",
            'timestamp': utils.timestamp()
        })
    
    except Exception as e:
        socketio.emit('log', {
            'nivel': 'ERROR',
            'msg': f"Error procesando mensaje USB: {str(e)}",
            'timestamp': utils.timestamp()
        })


def procesar_new_device(data):
    """Procesa nuevo dispositivo detectado (preserva clientes existentes)"""
    device_id = data.get('device_id')
    grupo = data.get('grupo', 0)
    role = data.get('role', '?')
    actividad = data.get('activity', 'Unknown')  # Campo "activity" desde micro:bit
    
    with estado_lock:
        # Buscar nombre en alumnos cargados
        nombre = None
        for alumno in estado['alumnos']:
            if alumno.get('id') == device_id:
                nombre = alumno.get('nombre')
                break
        
        # Si no tiene nombre, generar uno temporal
        if not nombre:
            from random import choice
            nombres_random = ["Luna", "Sol", "Estrella", "Cometa", "Nebulosa", 
                             "Galaxia", "Pulsar", "Quasar", "Asteroid", "Meteor"]
            nombre = f"{choice(nombres_random)}_{role}G{grupo}"
        
        # Si el dispositivo YA EXISTE, preservar cliente
        if device_id in estado['dispositivos']:
            dispositivo_existente = estado['dispositivos'][device_id]
            cliente_existente = dispositivo_existente.get('cliente')
            conectado_existente = dispositivo_existente.get('conectado', False)
            
            print(f"[Flask] Dispositivo EXISTENTE redescubierto: {nombre} [G{grupo}:{role}] - {actividad}")
            
            # Actualizar solo datos básicos (incluye actividad)
            estado['dispositivos'][device_id].update({
                'nombre': nombre,
                'grupo': grupo,
                'role': role,
                'actividad': actividad,
                'estado': 'registrado',
                'pendiente': False
            })
            
            # Preservar cliente Socket.IO si existe y está conectado
            if cliente_existente and conectado_existente:
                estado['dispositivos'][device_id]['cliente'] = cliente_existente
                estado['dispositivos'][device_id]['conectado'] = conectado_existente
                print(f"[Flask]   ✓ Cliente preservado (ya conectado a ClassQuiz)")
            
            socketio.emit('log', {
                'nivel': 'INFO',
                'msg': f"Redescubierto: {nombre} [G{grupo}:{role}] - {actividad} (cliente preservado)",
                'timestamp': utils.timestamp()
            })
            return
        
        # Si es NUEVO, crear desde cero
        print(f"[Flask] Nuevo dispositivo: {role} G{grupo} → {device_id[:8]} - {actividad}")
        
        estado['dispositivos'][device_id] = {
            'id': device_id,
            'nombre': nombre,
            'grupo': grupo,
            'role': role,
            'actividad': actividad,
            'estado': 'registrado',
            'pendiente': True,
            'cliente': None,
            'conectado': False
        }
    
    socketio.emit('log', {
        'nivel': 'INFO',
        'msg': f"Detectado: {nombre} [G{grupo}:{role}] - {actividad}",
        'timestamp': utils.timestamp()
    })



def procesar_discovery_end(data):
    """Procesa fin de descubrimiento"""
    total = data.get('total', 0)
    
    print(f"[Flask] Descubrimiento completo: {total} dispositivos")
    
    with estado_lock:
        dispositivos_list = list(estado['dispositivos'].values())
    
    socketio.emit('dispositivos_actualizados', {
        'dispositivos': dispositivos_list
    })
    
    socketio.emit('log', {
        'nivel': 'INFO',
        'msg': f"✅ Descubrimiento completo: {total} dispositivo(s) detectado(s)",
        'timestamp': utils.timestamp()
    })
    
    print("[Flask] Lista de dispositivos detectados:")
    for dev_id, info in estado['dispositivos'].items():
        print(f"[Flask]   - {info['nombre']} [G{info['grupo']}:{info['role']}] ({dev_id[:8]})")


def procesar_answer(data):
    """Procesa respuesta de estudiante"""
    device_id = data.get('device_id')
    grupo = data.get('grupo', 0)
    role = data.get('role', '?')
    respuesta = data.get('answer')
    
    with estado_lock:
        info = estado['dispositivos'].get(device_id, {})
        nombre = info.get('nombre', device_id[:8])
    
    print(f"[Flask] Respuesta: {nombre} [G{grupo}:{role}] → {respuesta}")
    
    socketio.emit('respuesta_recibida', {
        'device_id': device_id,
        'nombre': nombre,
        'grupo': grupo,
        'role': role,
        'respuesta': respuesta
    })
    
    socketio.emit('log', {
        'nivel': 'INFO',
        'msg': f"Respuesta: {nombre} [G{grupo}:{role}] → '{respuesta}'",
        'timestamp': utils.timestamp()
    })
    
    socketio_manager.enviar_respuesta(device_id, respuesta, estado)


# ============================================================================
# HELPERS
# ============================================================================

def guardar_config():
    """Guardar configuración en CSV"""
    utils.crear_directorio_data()
    
    try:
        with open(config.CONFIG_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'url', 'game_pin', 'puerto_serie', 'timeout_votacion'
            ])
            writer.writeheader()
            
            with estado_lock:
                writer.writerow({
                    'url': estado['url_classquiz'],
                    'game_pin': estado['game_pin'],
                    'puerto_serie': estado['puerto_nombre'] or '',
                    'timeout_votacion': estado['timeout_votacion']
                })
        
        print("[Flask] Configuración guardada correctamente")
        
    except Exception as e:
        print(f"[Flask] Error guardando configuración: {e}")


def run_server():
    """Ejecutar servidor Flask"""
    print(f"[Flask] Iniciando servidor en http://{config.FLASK_HOST}:{config.FLASK_PORT}")
    
    socketio.run(
        app,
        debug=False,
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        use_reloader=False,
        log_output=False
    )