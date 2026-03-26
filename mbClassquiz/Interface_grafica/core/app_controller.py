# core/app_controller.py
import threading
import webbrowser
import sys
from tkinter import messagebox

from core.gui.ventana import Ventana
from core import serial_manager, server, config
from app_registry import APPS

class AppController:
    def __init__(self, root):
        self.root       = root
        self.app_activa = None
        self.ventana    = Ventana(root, APPS)

        # Instancias permanentes por app_id
        self._instancias = {
            a["id"]: a["clase"]() for a in APPS
        }

        self._registrar_todos_los_blueprints()
        self._conectar_eventos()
        self._iniciar_servidor()
        serial_manager.registrar_on_estado(self._on_estado_serial)

        root.after(500, self._detectar_puertos)
        root.protocol("WM_DELETE_WINDOW", self._on_cerrar)

    def _registrar_todos_los_blueprints(self):
        """Registra todos los blueprints ANTES de iniciar el servidor."""
        for app_id, instancia in self._instancias.items():
            server.registrar_app(instancia.get_blueprint())

    def _conectar_eventos(self):
        self.ventana.btn_detectar.config(command=self._detectar_puertos)
        self.ventana.btn_conectar.config(command=self._conectar_puerto)
        self.ventana.btn_desconectar.config(command=self._desconectar_puerto)
        for app_def in APPS:
            aid = app_def["id"]
            self.ventana.botones_apps[aid].config(
                command=lambda a=aid: self._abrir_app(a))

    def _iniciar_servidor(self):
        threading.Thread(target=server.run, daemon=True).start()

    def _detectar_puertos(self):
        try:
            puertos = serial_manager.detectar_puertos()
            self.ventana.set_puertos([p['port'] for p in puertos])
        except Exception as e:
            print(f"[Controller] Error detectando puertos: {e}")

    def _conectar_puerto(self):
        puerto = self.ventana.puerto_seleccionado.get()
        if not puerto:
            messagebox.showwarning("Aviso", "Selecciona un puerto primero.")
            return
        if serial_manager.conectar(puerto):
            self.ventana.set_conectado(True, puerto)
            serial_manager.iniciar_loop()
        else:
            messagebox.showerror("Error", f"No se pudo conectar a {puerto}")

    def _desconectar_puerto(self):
        if self.app_activa:
            self.app_activa.on_stop()
            self.app_activa = None
            serial_manager.registrar_callback(None)
        serial_manager.desconectar()
        self.ventana.set_conectado(False)

    def _on_estado_serial(self, conectado: bool, puerto: str = ""):
        if conectado:
            self.root.after(0, lambda: self.ventana.set_conectado(True, puerto))
        else:
            if serial_manager._loop_activo:
                self.root.after(0, self.ventana.set_reconectando)
            else:
                self.root.after(0, lambda: self.ventana.set_conectado(False))

    def _abrir_app(self, app_id):
        # Detener app anterior
        if self.app_activa:
            self.app_activa.on_stop()
            serial_manager.registrar_callback(None)

        # Reusar instancia permanente (el estado interno lo resetea on_stop/on_start)
        self.app_activa = self._instancias[app_id]
        serial_manager.registrar_callback(self.app_activa.on_message)
        self.app_activa.on_start()

        url = f"http://localhost:{config.FLASK_PORT}/{app_id}/"
        webbrowser.open(url)

    def _on_cerrar(self):
        if messagebox.askokcancel("Salir", "¿Cerrar la aplicación?"):
            if self.app_activa:
                self.app_activa.on_stop()
            serial_manager.desconectar()
            self.root.destroy()
            sys.exit(0)