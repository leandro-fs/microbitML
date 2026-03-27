# core/gui/ventana.py
import tkinter as tk
from tkinter import ttk

class Ventana:
    def __init__(self, root, apps: list):
        self.root = root
        self.root.title("Microbit Proxy")
        self.root.geometry("420x360")
        self.root.resizable(False, False)

        self.puerto_seleccionado = tk.StringVar()
        self.estado_var          = tk.StringVar(value="🔴 Desconectado")

        self._construir(apps)

    def _construir(self, apps):
        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        tk.Label(main, text="📟 Microbit Proxy",
                 font=("Arial", 15, "bold")).pack(pady=(0, 15))

        # --- Sección USB ---
        usb_frame = ttk.LabelFrame(main, text="Conexión USB", padding=10)
        usb_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(usb_frame, text="Puerto:").grid(row=0, column=0, sticky=tk.W)
        self.puerto_combo = ttk.Combobox(
            usb_frame, textvariable=self.puerto_seleccionado,
            state="readonly", width=18)
        self.puerto_combo.grid(row=0, column=1, padx=(10, 0))

        btn_usb = ttk.Frame(usb_frame)
        btn_usb.grid(row=1, column=0, columnspan=2, pady=(8, 0))

        self.btn_detectar    = ttk.Button(btn_usb, text="🔍 Detectar")
        self.btn_detectar.pack(side=tk.LEFT, padx=4)

        self.btn_conectar    = ttk.Button(btn_usb, text="🔌 Conectar")
        self.btn_conectar.pack(side=tk.LEFT, padx=4)

        self.btn_desconectar = ttk.Button(btn_usb, text="⏏ Desconectar", state=tk.DISABLED)
        self.btn_desconectar.pack(side=tk.LEFT, padx=4)

        # --- Estado ---
        estado_frame = ttk.Frame(main)
        estado_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(estado_frame, text="Estado:").pack(side=tk.LEFT)
        self.estado_label = tk.Label(
            estado_frame, textvariable=self.estado_var,
            font=("Arial", 11, "bold"), fg="red")
        self.estado_label.pack(side=tk.LEFT, padx=8)

        # --- Botones de apps ---
        apps_frame = ttk.LabelFrame(main, text="Actividades", padding=10)
        apps_frame.pack(fill=tk.X)

        self.botones_apps = {}
        for app in apps:
            btn = ttk.Button(apps_frame, text=app["label"])
            btn.pack(side=tk.LEFT, padx=6)
            self.botones_apps[app["id"]] = btn

    def set_conectado(self, conectado: bool, puerto: str = ""):
        if conectado:
            self.estado_var.set(f"🟢 {puerto}")
            self.estado_label.config(fg="green")
            self.btn_conectar.config(state=tk.DISABLED)
            self.btn_desconectar.config(state=tk.NORMAL)
        else:
            self.estado_var.set("🔴 Desconectado")
            self.estado_label.config(fg="red")
            self.btn_conectar.config(state=tk.NORMAL)
            self.btn_desconectar.config(state=tk.DISABLED)

    def set_reconectando(self):
        """Muestra estado intermedio durante reintentos automáticos."""
        self.estado_var.set("🟡 Reconectando...")
        self.estado_label.config(fg="orange")
        self.btn_conectar.config(state=tk.DISABLED)
        self.btn_desconectar.config(state=tk.NORMAL)

    def set_puertos(self, puertos: list):
        self.puerto_combo['values'] = puertos
        if puertos:
            self.puerto_combo.current(0)