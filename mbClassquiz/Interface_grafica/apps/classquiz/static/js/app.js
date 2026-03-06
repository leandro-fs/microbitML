// apps/classquiz/static/js/app.js
// Sistema Proxy Microbit-ClassQuiz v1.2
// MODIFICADO: rutas actualizadas a /classquiz/api/

const BASE = '/classquiz';
const socket = io('http://localhost:5000');

const state = {
    dispositivos: {},
    logs: [],
    debugVisible: true,
    autoScroll: true,
    preguntaActiva: null,
    countdownInterval: null
};

// ============================================================================
// EVENTOS SOCKET.IO
// ============================================================================

socket.on('connect', () => {
    console.log('[Socket.IO] Conectado al servidor');
    actualizarEstadoConexion(true);
    agregarLog('INFO', 'Conectado al servidor Flask');
    // Cargar dispositivos existentes al conectar
    fetch(`${BASE}/api/dispositivos`)
        .then(r => r.json())
        .then(data => {
            data.dispositivos.forEach(d => {
                state.dispositivos[d.device_id] = d;
            });
            actualizarTablaDispositivos();
            actualizarEstadisticas();
        });
});

socket.on('disconnect', () => {
    console.log('[Socket.IO] Desconectado del servidor');
    actualizarEstadoConexion(false);
    agregarLog('WARNING', 'Desconectado del servidor Flask');
});

socket.on('log', (data) => {
    agregarLog(data.nivel, data.msg, data.timestamp);
});

socket.on('dispositivos_actualizados', (data) => {
    const nuevosDispositivos = {};
    if (Array.isArray(data.dispositivos)) {
        data.dispositivos.forEach(disp => {
            const id = disp.id || disp.device_id;
            if (id) nuevosDispositivos[id] = disp;
        });
    }
    state.dispositivos = nuevosDispositivos;
    actualizarTablaDispositivos();
    actualizarEstadisticas();
});

socket.on('new_device', (data) => {
    console.log('[Socket.IO] new_device:', data);
    const id = data.device_id;
    if (id) {
        state.dispositivos[id] = {
            device_id: id,
            grp:       data.grp,
            rol:       data.rol,
            nombre:    data.nombre || id.substring(0, 8),
            estado:    'registrado',
            actividad: data.actividad || '',
            conectado: false
        };
        actualizarTablaDispositivos();
        actualizarEstadisticas();
    }
});

socket.on('discovery_end', (data) => {
    console.log('[Socket.IO] discovery_end:', data);
    actualizarTablaDispositivos();
    actualizarEstadisticas();
});

socket.on('device_connected', (data) => {
    if (state.dispositivos[data.device_id]) {
        state.dispositivos[data.device_id].conectado = true;
        state.dispositivos[data.device_id].estado    = 'online';
        actualizarTablaDispositivos();
        actualizarEstadisticas();
    }
});

socket.on('device_renamed', (data) => {
    if (state.dispositivos[data.device_id]) {
        state.dispositivos[data.device_id].nombre = data.nombre;
        const input = document.querySelector(`input[data-device-id="${data.device_id}"]`);
        if (input) input.value = data.nombre;
    }
});

socket.on('respuesta_recibida', (data) => {
    const grupo = data.grupo || '?';
    const role  = data.role  || '?';
    agregarLog('INFO', `Respuesta: ${data.nombre} [G${grupo}:${role}] → ${data.respuesta}`);
    actualizarRespuestaEnLista(data.device_id, data.nombre, data.respuesta);
});

socket.on('countdown', (data) => {
    actualizarCountdown(data.segundos);
});

socket.on('pregunta_nueva', (data) => {
    state.preguntaActiva = data;
    mostrarPanelPregunta(data);
    agregarLog('INFO', `Nueva pregunta: ${data.tipo} con ${data.num_opciones} opciones`);
});

socket.on('config_cargada', (data) => {
    agregarLog('INFO', 'Configuración cargada desde archivo CSV');
    if (data.url)     document.getElementById('url-input').value     = data.url;
    if (data.pin)     document.getElementById('pin-input').value     = data.pin;
    if (data.timeout) document.getElementById('timeout-input').value = data.timeout;

    if (data.alumnos && Array.isArray(data.alumnos)) {
        const nuevosDispositivos = {};
        data.alumnos.forEach(alumno => {
            if (alumno.id) {
                nuevosDispositivos[alumno.id] = {
                    device_id: alumno.id,
                    nombre:    alumno.nombre,
                    grp:       alumno.grp  || '',
                    rol:       alumno.rol  || '',
                    actividad: alumno.actividad || '',
                    estado:    alumno.estado || 'registrado',
                    conectado: false
                };
            }
        });
        state.dispositivos = nuevosDispositivos;
        actualizarTablaDispositivos();
        actualizarEstadisticas();
        agregarLog('INFO', `${data.alumnos.length} alumnos cargados en tabla`);
    }
});

// ============================================================================
// FUNCIONES UI
// ============================================================================

function actualizarEstadoConexion(conectado) {
    const badge = document.getElementById('status-badge');
    if (conectado) {
        badge.textContent = '🟢 Conectado';
        badge.className   = 'badge bg-success';
    } else {
        badge.textContent = '🔴 Desconectado';
        badge.className   = 'badge bg-danger';
    }
}

function agregarLog(nivel, msg, timestamp) {
    const ts = timestamp || new Date().toLocaleTimeString();
    state.logs.push({ nivel, msg, timestamp: ts });

    if (nivel === 'DEBUG' && !state.debugVisible) return;

    const busqueda = document.getElementById('buscar-input').value.toLowerCase();
    if (busqueda && !msg.toLowerCase().includes(busqueda)) return;

    const lista     = document.getElementById('log-list');
    const container = document.getElementById('log-container');
    const li        = document.createElement('li');
    li.className    = `list-group-item log-item ${nivel}`;
    li.textContent  = `[${ts}] [${nivel}] ${msg}`;
    lista.appendChild(li);

    if (state.autoScroll) container.scrollTop = container.scrollHeight;
}

function refrescarLogs() {
    const lista = document.getElementById('log-list');
    lista.innerHTML = '';
    state.logs.forEach(log => {
        if (log.nivel === 'DEBUG' && !state.debugVisible) return;
        const li    = document.createElement('li');
        li.className = `list-group-item log-item ${log.nivel}`;
        li.textContent = `[${log.timestamp}] [${log.nivel}] ${log.msg}`;
        lista.appendChild(li);
    });
}

function actualizarTablaDispositivos() {
    const tbody      = document.getElementById('dispositivos-tbody');
    tbody.innerHTML  = '';
    const dispositivos = Object.entries(state.dispositivos);

    if (dispositivos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No hay dispositivos registrados</td></tr>';
        return;
    }

    dispositivos.forEach(([device_id, info]) => {
        const tr = document.createElement('tr');

        const tdId = document.createElement('td');
        tdId.className   = 'text-monospace small';
        tdId.textContent = device_id.substring(0, 8) + '...';
        tdId.title       = device_id;

        const tdNombre      = document.createElement('td');
        const inputNombre   = document.createElement('input');
        inputNombre.type        = 'text';
        inputNombre.className   = 'nombre-input';
        inputNombre.value       = info.nombre || '';
        inputNombre.placeholder = 'Nombre del alumno';
        inputNombre.dataset.deviceId = device_id;
        inputNombre.addEventListener('input', (e) => {
            state.dispositivos[device_id].nombre = e.target.value.trim();
        });
        inputNombre.addEventListener('change', (e) => {
            const nuevoNombre = e.target.value.trim();
            if (nuevoNombre) {
                state.dispositivos[device_id].nombre = nuevoNombre;
                fetch(`${BASE}/api/renombrar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ device_id, nombre: nuevoNombre })
                });
            }
        });
        tdNombre.appendChild(inputNombre);

        const tdGrupo = document.createElement('td');
        tdGrupo.className = 'text-center';
        tdGrupo.innerHTML = `<span class="badge bg-secondary">${info.grp ?? '?'}</span>`;

        const tdRole = document.createElement('td');
        tdRole.className = 'text-center';
        tdRole.innerHTML = `<span class="badge bg-info">${info.rol ?? '?'}</span>`;

        const tdEstado = document.createElement('td');
        const estado   = info.estado || 'offline';
        const estadoMap = {
            'online':       ['🟢 Online',       'estado-online'],
            'registrado':   ['🟡 Registrado',   'estado-registrado'],
            'desconectado': ['🔴 Desconectado', 'estado-desconectado'],
        };
        const [texto, clase] = estadoMap[estado] || ['⚪ Offline', 'estado-offline'];
        tdEstado.innerHTML = `<span class="${clase}">${texto}</span>`;

        const tdActividad = document.createElement('td');
        tdActividad.className = 'text-center';
        tdActividad.innerHTML = `<span class="badge bg-success">${info.actividad || '?'}</span>`;

        tr.append(tdId, tdNombre, tdGrupo, tdRole, tdEstado, tdActividad);
        tbody.appendChild(tr);
    });
}

function actualizarEstadisticas() {
    const total     = Object.keys(state.dispositivos).length;
    const conectados = Object.values(state.dispositivos).filter(d => d.conectado || d.estado === 'online').length;
    document.getElementById('stats-text').textContent = `Total: ${total} alumnos / ${conectados} conectados`;
}

function mostrarPanelPregunta(pregunta) {
    document.getElementById('pregunta-panel').classList.remove('d-none');
    document.getElementById('pregunta-info').innerHTML =
        `<strong>Pregunta #${pregunta.index}:</strong> ${pregunta.tipo} con ${pregunta.num_opciones} opciones`;

    const lista = document.getElementById('respuestas-list');
    lista.innerHTML = '';
    Object.entries(state.dispositivos).forEach(([device_id, info]) => {
        const li         = document.createElement('li');
        li.className     = 'list-group-item d-flex justify-content-between align-items-center';
        li.id            = `respuesta-${device_id}`;
        const nombre     = info.nombre || device_id.substring(0, 8);
        const grupo      = info.grp ?? '?';
        const role       = info.rol ?? '?';
        li.innerHTML     = `<span>${nombre} <small class="text-muted">[G${grupo}:${role}]</small></span>
                            <span class="badge bg-secondary">Esperando...</span>`;
        lista.appendChild(li);
    });
    actualizarCountdown(pregunta.timeout || 30);
}

function actualizarCountdown(segundos) {
    const el = document.getElementById('countdown-info');
    if (segundos > 0) {
        el.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-warning text-dark">${segundos}s</span>`;
    } else {
        el.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-danger">Completo</span>`;
    }
}

function actualizarRespuestaEnLista(device_id, nombre, respuesta) {
    const li = document.getElementById(`respuesta-${device_id}`);
    if (li) {
        const badge = li.querySelector('.badge');
        badge.textContent = respuesta || '(vacía)';
        badge.className   = 'badge bg-success';
    }
}

function ocultarPanelPregunta() {
    document.getElementById('pregunta-panel').classList.add('d-none');
    state.preguntaActiva = null;
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

document.getElementById('guardar-todo-btn').addEventListener('click', async () => {
    const url           = document.getElementById('url-input').value.trim();
    const pin           = document.getElementById('pin-input').value.trim();
    const timeout       = parseInt(document.getElementById('timeout-input').value);
    const nombreArchivo = document.getElementById('nombre-archivo-input').value.trim();

    if (!url || !pin)      { alert('Por favor completa URL y PIN'); return; }
    if (!nombreArchivo)    { alert('Por favor ingresa un nombre para el archivo'); return; }

    try {
        agregarLog('INFO', `Generando archivo: ${nombreArchivo}.csv`);
        const response = await fetch(`${BASE}/api/guardar_todo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url, pin, timeout,
                nombre_archivo: nombreArchivo,
                alumnos: Object.entries(state.dispositivos).map(([id, info]) => ({
                    id, nombre: info.nombre || '', grupo: info.grp || '', role: info.rol || ''
                }))
            })
        });

        if (response.ok) {
            const blob        = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a           = document.createElement('a');
            a.href     = downloadUrl;
            a.download = `${nombreArchivo}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            localStorage.setItem('ultimo_archivo', nombreArchivo);
            agregarLog('INFO', `✅ Archivo descargado: ${nombreArchivo}.csv`);
        } else {
            const data = await response.json();
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        agregarLog('ERROR', `Error guardando: ${error.message}`);
    }
});

document.getElementById('conectar-classquiz-btn').addEventListener('click', async () => {
    const url     = document.getElementById('url-input').value.trim();
    const pin     = document.getElementById('pin-input').value.trim();
    const timeout = parseInt(document.getElementById('timeout-input').value);

    if (!url || !pin) { alert('Por favor completa URL y PIN'); return; }
    if (isNaN(timeout) || timeout < 0) { alert('Timeout debe ser >= 0'); return; }

    const numDispositivos = Object.keys(state.dispositivos).length;
    if (numDispositivos === 0) {
        alert('⚠️ No hay dispositivos detectados.\n\nPresiona "Descubrir Dispositivos" primero.');
        agregarLog('ERROR', 'No hay dispositivos para conectar');
        return;
    }

    if (!confirm(`🔄 Conectar ${numDispositivos} dispositivo(s) a:\n📍 ${url}\n🔑 PIN: ${pin}\n\n¿Continuar?`)) return;

    const statusAlert = document.getElementById('status-conexion-alert');
    const statusTexto = document.getElementById('status-conexion-texto');
    statusAlert.classList.remove('d-none');
    statusTexto.textContent   = '🔄 Conectando...';
    statusAlert.className     = 'alert alert-info mt-3';

    try {
        const response = await fetch(`${BASE}/api/conectar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, pin, timeout })
        });
        const data = await response.json();

        if (response.ok && data.status === 'ok') {
            agregarLog('INFO', `✅ Conexión iniciada`);
            statusTexto.textContent = `✅ Dispositivos conectándose...`;
            statusAlert.className   = 'alert alert-success mt-3';
            setTimeout(() => statusAlert.classList.add('d-none'), 5000);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        agregarLog('ERROR', `Error conectando: ${error.message}`);
        statusTexto.textContent = `❌ ${error.message}`;
        statusAlert.className   = 'alert alert-danger mt-3';
    }
});

document.getElementById('descubrir-btn').addEventListener('click', async () => {
    agregarLog('INFO', 'Iniciando descubrimiento...');
    try {
        const response = await fetch(`${BASE}/api/descubrir`, { method: 'POST' });
        const data     = await response.json();
        if (data.status === 'ok') {
            agregarLog('INFO', 'Descubrimiento iniciado');
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        agregarLog('ERROR', `Error en descubrimiento: ${error.message}`);
    }
});

document.getElementById('cargar-config-btn').addEventListener('click', () => {
    const input  = document.createElement('input');
    input.type   = 'file';
    input.accept = '.csv';

    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        agregarLog('INFO', `Cargando archivo: ${file.name}`);

        try {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`${BASE}/api/cargar_config`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            if (data.status === 'ok') {
                if (data.url)     document.getElementById('url-input').value     = data.url;
                if (data.pin)     document.getElementById('pin-input').value     = data.pin;
                if (data.timeout) document.getElementById('timeout-input').value = data.timeout;
                const nombreBase = file.name.replace('.csv', '');
                document.getElementById('nombre-archivo-input').value = nombreBase;
                localStorage.setItem('ultimo_archivo', nombreBase);
                agregarLog('INFO', `✅ Cargado: ${file.name} (${data.alumnos_cargados || 0} alumnos)`);
            } else {
                throw new Error(data.error || 'Error desconocido');
            }
        } catch (error) {
            agregarLog('ERROR', `Error cargando: ${error.message}`);
        }
    };
    input.click();
});

document.getElementById('finalizar-btn').addEventListener('click', () => {
    if (confirm('¿Finalizar votación ahora?')) {
        socket.emit('finalizar_votacion');
        agregarLog('INFO', 'Votación finalizada manualmente');
        ocultarPanelPregunta();
    }
});

document.getElementById('debug-checkbox').addEventListener('change', (e) => {
    state.debugVisible = e.target.checked;
    refrescarLogs();
});

document.getElementById('exportar-btn').addEventListener('click', () => {
    const texto = state.logs.map(l => `[${l.timestamp}] [${l.nivel}] ${l.msg}`).join('\n');
    const blob  = new Blob([texto], { type: 'text/plain' });
    const url   = URL.createObjectURL(blob);
    const a     = document.createElement('a');
    a.href      = url;
    a.download  = `logs_${new Date().toISOString().replace(/:/g, '-')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
});

document.getElementById('buscar-input').addEventListener('input', (e) => {
    const busqueda = e.target.value.toLowerCase();
    document.querySelectorAll('.log-item').forEach(item => {
        item.style.display = item.textContent.toLowerCase().includes(busqueda) ? '' : 'none';
    });
});

let pauseTimeout = null;
document.getElementById('log-container').addEventListener('click', () => {
    const container = document.getElementById('log-container');
    state.autoScroll = false;
    container.classList.add('paused');
    if (pauseTimeout) clearTimeout(pauseTimeout);
    pauseTimeout = setTimeout(() => {
        state.autoScroll = true;
        container.classList.remove('paused');
    }, 5000);
});

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

window.addEventListener('load', async () => {
    agregarLog('INFO', 'Interface web cargada');
    const ultimoArchivo = localStorage.getItem('ultimo_archivo');
    if (ultimoArchivo) document.getElementById('nombre-archivo-input').value = ultimoArchivo;

    try {
        const response = await fetch(`${BASE}/api/config`);
        const data     = await response.json();
        if (data.url)     document.getElementById('url-input').value     = data.url;
        if (data.pin)     document.getElementById('pin-input').value     = data.pin;
        if (data.timeout) document.getElementById('timeout-input').value = data.timeout;
    } catch (error) {
        console.error('Error cargando config inicial:', error);
    }
});