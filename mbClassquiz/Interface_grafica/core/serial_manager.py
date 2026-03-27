# core/serial_manager.py
import serial
import serial.tools.list_ports
import json
import time
import threading
from threading import Lock

from core import config

_puerto_serial   = None
_puerto_nombre   = None          # guarda el nombre del puerto para reconexión
_puerto_lock     = Lock()
_callback        = None
_loop_activo     = False         # True mientras el loop de lectura debe correr
_loop_lock       = Lock()

# Cuántas veces reintentar reconexión y cada cuántos segundos
REINTENTOS_MAX   = 10
ESPERA_REINTENTO = 3             # segundos entre intentos

# Callable opcional para notificar cambios de estado a la GUI
# Firma: fn(conectado: bool, puerto: str)
_on_estado_cambio = None

def registrar_callback(fn):
    global _callback
    _callback = fn

def registrar_on_estado(fn):
    """Registra un callable que se llama cuando cambia el estado de conexión."""
    global _on_estado_cambio
    _on_estado_cambio = fn

def _notificar_estado(conectado: bool, puerto: str = ""):
    if _on_estado_cambio:
        try:
            _on_estado_cambio(conectado, puerto)
        except Exception:
            pass

def detectar_puertos():
    return [{'port': p.device, 'description': p.description}
            for p in serial.tools.list_ports.comports()]

def conectar(puerto):
    global _puerto_serial, _puerto_nombre
    try:
        with _puerto_lock:
            if _puerto_serial and _puerto_serial.is_open:
                _puerto_serial.close()
            _puerto_serial = serial.Serial(puerto, config.BAUDRATE, timeout=config.SERIAL_TIMEOUT)
            _puerto_nombre = puerto
            time.sleep(2)
        print(f"[Serial] Conectado a {puerto}")
        _notificar_estado(True, puerto)
        return True
    except Exception as e:
        print(f"[Serial] Error conectando: {e}")
        return False

def desconectar():
    global _puerto_serial, _puerto_nombre, _loop_activo
    with _loop_lock:
        _loop_activo = False
    try:
        with _puerto_lock:
            if _puerto_serial and _puerto_serial.is_open:
                _puerto_serial.close()
            _puerto_serial = None
            _puerto_nombre = None
    except Exception as e:
        print(f"[Serial] Error desconectando: {e}")
    _notificar_estado(False)
    print("[Serial] Desconectado")

def esta_conectado():
    try:
        with _puerto_lock:
            return _puerto_serial is not None and _puerto_serial.is_open
    except Exception:
        return False

def enviar(data):
    if not esta_conectado():
        return False
    try:
        with _puerto_lock:
            _puerto_serial.write((json.dumps(data, separators=(',', ':')) + '\n').encode('utf-8'))
            _puerto_serial.flush()
        return True
    except Exception as e:
        print(f"[Serial] Error enviando: {e}")
        return False

class ErrorHardwareSerial(Exception):
    """Se lanza cuando el puerto serial detecta un error de hardware (desconexión física)."""
    pass

def leer():
    if not esta_conectado():
        return None
    try:
        with _puerto_lock:
            if _puerto_serial.in_waiting > 0:
                linea = _puerto_serial.readline().decode('utf-8', errors='ignore').strip()
                return linea if linea else None
    except serial.SerialException as e:
        raise ErrorHardwareSerial(str(e))
    except Exception as e:
        # PermissionError en Windows indica desconexión física
        if isinstance(e, PermissionError) or 'ClearCommError' in str(e) or 'PermissionError' in str(e):
            raise ErrorHardwareSerial(str(e))
        print(f"[Serial] Error leyendo: {e}")
    return None

def _forzar_cierre():
    """Cierra el puerto sin modificar _loop_activo ni _puerto_nombre."""
    global _puerto_serial
    try:
        with _puerto_lock:
            if _puerto_serial and _puerto_serial.is_open:
                _puerto_serial.close()
            _puerto_serial = None
    except Exception:
        pass

def loop_lectura():
    """
    Loop principal de lectura. Maneja desconexiones y reconexión automática.
    Solo debe haber una instancia corriendo a la vez (_loop_activo lo garantiza).
    """
    global _loop_activo

    with _loop_lock:
        if _loop_activo:
            print("[Serial] Loop ya activo, ignorando nueva solicitud")
            return
        _loop_activo = True

    print("[Serial] Loop de lectura iniciado")

    while True:
        with _loop_lock:
            if not _loop_activo:
                break

        if esta_conectado():
            try:
                linea = leer()
                if linea and _callback:
                    try:
                        msg = json.loads(linea)
                        _callback(msg)
                    except json.JSONDecodeError:
                        print(f"[Serial] JSON invalido: {linea}")
                time.sleep(config.USB_READ_INTERVAL)
            except ErrorHardwareSerial as e:
                print(f"[Serial] Desconexion fisica detectada: {e}")
                _forzar_cierre()
                # Cae al bloque else en la siguiente iteración
            except Exception as e:
                print(f"[Serial] Error en loop: {e}")
                time.sleep(1)
        else:
            # Puerto perdido — intentar reconexión automática
            puerto = _puerto_nombre
            if not puerto:
                break   # nunca hubo puerto, salir

            print(f"[Serial] Conexion perdida. Reconectando {puerto} en {ESPERA_REINTENTO}s...")
            _notificar_estado(False)

            reconectado = False
            for intento in range(1, REINTENTOS_MAX + 1):
                with _loop_lock:
                    if not _loop_activo:
                        break
                time.sleep(ESPERA_REINTENTO)
                print(f"[Serial] Reintento {intento}/{REINTENTOS_MAX}...")
                if conectar(puerto):
                    reconectado = True
                    break

            if not reconectado:
                print("[Serial] No se pudo reconectar. Loop finalizado.")
                with _loop_lock:
                    _loop_activo = False
                _notificar_estado(False)
                break

    print("[Serial] Loop de lectura finalizado")

def iniciar_loop():
    """Lanza el loop en un hilo daemon si no está corriendo."""
    threading.Thread(target=loop_lectura, daemon=True).start()