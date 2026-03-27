# apps/monitor/app.py
import os
from flask import Blueprint, send_from_directory
from core.base_app import BaseApp
from core.server import socketio
from core import utils

class MonitorApp(BaseApp):
    id    = "monitor"
    label = "🔍 Monitor USB"

    def get_blueprint(self):
        template_dir = os.path.join(os.path.dirname(__file__), 'templates', 'monitor')

        bp = Blueprint('monitor', __name__,
                       template_folder='templates',
                       static_folder='static',
                       url_prefix='/monitor')

        @bp.route('/')
        def index():
            return send_from_directory(template_dir, 'index.html')

        return bp

    def on_start(self):
        print("[Monitor] Iniciado")

    def on_stop(self):
        print("[Monitor] Detenido")

    def on_message(self, msg: dict):
        socketio.emit('usb_message', {
            'msg': msg,
            'timestamp': utils.timestamp()
        })