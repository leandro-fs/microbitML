# core/serial_manager.py
import serial
import serial.tools.list_ports
import json
import time
from threading import Lock

from core import config

_puerto_serial = None
_puerto_lock   = Lock()
_callback      = None

def registrar_callback(fn):
    global _callback
    _callback = fn

def detectar_puertos():
    return [{'port': p.device, 'description': p.description}
            for p in serial.tools.list_ports.comports()]

def conectar(puerto):
    global _puerto_serial
    try:
        with _puerto_lock:
            if _puerto_serial and _puerto_serial.is_open:
                _puerto_serial.close()
            _puerto_serial = serial.Serial(puerto, config.BAUDRATE, timeout=config.SERIAL_TIMEOUT)
            time.sleep(2)
        print(f"[Serial] Conectado a {puerto}")
        return True
    except Exception as e:
        print(f"[Serial] Error: {e}")
        return False

def desconectar():
    global _puerto_serial
    try:
        with _puerto_lock:
            if _puerto_serial and _puerto_serial.is_open:
                _puerto_serial.close()
            _puerto_serial = None
    except Exception as e:
        print(f"[Serial] Error desconectando: {e}")

def esta_conectado():
    try:
        with _puerto_lock:
            return _puerto_serial is not None and _puerto_serial.is_open
    except:
        return False

def enviar(data):
    if not esta_conectado():
        return False
    try:
        with _puerto_lock:
            # separators=(',',':') elimina espacios — critico para el parser del concentrador
            _puerto_serial.write((json.dumps(data, separators=(',', ':')) + '\n').encode('utf-8'))
            _puerto_serial.flush()
        return True
    except Exception as e:
        print(f"[Serial] Error enviando: {e}")
        return False

def leer():
    if not esta_conectado():
        return None
    try:
        with _puerto_lock:
            if _puerto_serial.in_waiting > 0:
                linea = _puerto_serial.readline().decode('utf-8', errors='ignore').strip()
                return linea if linea else None
    except Exception as e:
        print(f"[Serial] Error leyendo: {e}")
    return None

def loop_lectura():
    print("[Serial] Loop de lectura iniciado")
    while esta_conectado():
        try:
            linea = leer()
            if linea and _callback:
                try:
                    msg = json.loads(linea)
                    _callback(msg)
                except json.JSONDecodeError:
                    print(f"[Serial] JSON invalido: {linea}")
            time.sleep(config.USB_READ_INTERVAL)
        except Exception as e:
            print(f"[Serial] Error en loop: {e}")
            time.sleep(1)
    print("[Serial] Loop de lectura finalizado")