// app.js - Lógica frontend del sistema
// Sistema Proxy Microbit-ClassQuiz v1.2
// ACTUALIZADO: Desconexión previa + Sincronización nombres + Config dinámica

// ============================================================================
// CONEXIÓN SOCKET.IO
// ============================================================================

const socket = io('http://localhost:5000');

// ============================================================================
// ESTADO GLOBAL
// ============================================================================

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
    // Convertir array a objeto con device_id como key
    const nuevosDispositivos = {};
    
    if (Array.isArray(data.dispositivos)) {
        data.dispositivos.forEach(disp => {
            const id = disp.id || disp.device_id;
            if (id) {
                nuevosDispositivos[id] = disp;
            }
        });
    }
    
    state.dispositivos = nuevosDispositivos;
    actualizarTablaDispositivos();
    actualizarEstadisticas();
});

socket.on('respuesta_recibida', (data) => {
    const grupo = data.grupo || '?';
    const role = data.role || '?';
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

    // Actualizar inputs
    if (data.url) document.getElementById('url-input').value = data.url;
    if (data.pin) document.getElementById('pin-input').value = data.pin;
    if (data.timeout) document.getElementById('timeout-input').value = data.timeout;

    // Actualizar dispositivos desde alumnos
    if (data.alumnos && Array.isArray(data.alumnos)) {
        const nuevosDispositivos = {};
        data.alumnos.forEach(alumno => {
            if (alumno.id) {
                nuevosDispositivos[alumno.id] = {
                    id: alumno.id,
                    nombre: alumno.nombre,
                    grupo: alumno.grupo || '',
                    role: alumno.role || '',
                    estado: alumno.estado || 'offline'
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
// FUNCIONES UI - ESTADO CONEXIÓN
// ============================================================================

function actualizarEstadoConexion(conectado) {
    const badge = document.getElementById('status-badge');
    
    if (conectado) {
        badge.textContent = '🟢 Conectado';
        badge.className = 'badge bg-success';
    } else {
        badge.textContent = '🔴 Desconectado';
        badge.className = 'badge bg-danger';
    }
}

// ============================================================================
// FUNCIONES UI - LOGS
// ============================================================================

function agregarLog(nivel, mensaje, timestamp) {
    const log = {
        nivel: nivel,
        msg: mensaje,
        timestamp: timestamp || new Date().toLocaleTimeString()
    };
    
    state.logs.push(log);
    
    // Limitar a últimos 500 logs
    if (state.logs.length > 500) {
        state.logs.shift();
    }
    
    // Renderizar solo si es visible o no es DEBUG
    if (state.debugVisible || nivel !== 'DEBUG') {
        renderizarLog(log);
    }
}

function renderizarLog(log) {
    const logList = document.getElementById('log-list');
    
    const li = document.createElement('li');
    li.className = `list-group-item log-item ${log.nivel}`;
    li.textContent = `[${log.timestamp}] ${log.msg}`;
    
    logList.appendChild(li);
    
    // Auto-scroll si está habilitado
    if (state.autoScroll) {
        const container = document.getElementById('log-container');
        container.scrollTop = container.scrollHeight;
    }
}

function limpiarLogs() {
    document.getElementById('log-list').innerHTML = '';
}

function refrescarLogs() {
    limpiarLogs();
    
    state.logs.forEach(log => {
        if (state.debugVisible || log.nivel !== 'DEBUG') {
            renderizarLog(log);
        }
    });
}

// ============================================================================
// FUNCIONES UI - DISPOSITIVOS
// ============================================================================

function actualizarTablaDispositivos() {
    const tbody = document.getElementById('dispositivos-tbody');
    tbody.innerHTML = '';
    
    const dispositivos = Object.entries(state.dispositivos);
    
    if (dispositivos.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="6" class="text-center text-muted">No hay dispositivos registrados</td>';
        tbody.appendChild(tr);
        return;
    }
    
    dispositivos.forEach(([device_id, info]) => {
        const tr = document.createElement('tr');
        
        // Device ID (acortado)
        const tdId = document.createElement('td');
        tdId.className = 'text-monospace small';
        tdId.textContent = device_id.substring(0, 8) + '...';
        tdId.title = device_id;
        
        // Nombre (editable con sincronización)
        const tdNombre = document.createElement('td');
        const inputNombre = document.createElement('input');
        inputNombre.type = 'text';
        inputNombre.className = 'nombre-input';
        inputNombre.value = info.nombre || '';
        inputNombre.placeholder = 'Nombre del alumno';
        inputNombre.dataset.deviceId = device_id;
        
        // ⭐ Sincronización con backend
        inputNombre.addEventListener('change', (e) => {
            const nuevoNombre = e.target.value.trim();
            if (nuevoNombre) {
                state.dispositivos[device_id].nombre = nuevoNombre;
                
                socket.emit('actualizar_nombre', {
                    device_id: device_id,
                    nombre: nuevoNombre
                });
                
                console.log(`[Frontend] Nombre actualizado: ${device_id.substring(0, 8)} → ${nuevoNombre}`);
            }
        });
        
        tdNombre.appendChild(inputNombre);
        
        // Grupo
        const tdGrupo = document.createElement('td');
        tdGrupo.className = 'text-center';
        const grupo = info.grupo || '?';
        tdGrupo.innerHTML = `<span class="badge bg-secondary">${grupo}</span>`;
        
        // Rol
        const tdRole = document.createElement('td');
        tdRole.className = 'text-center';
        const role = info.role || '?';
        tdRole.innerHTML = `<span class="badge bg-info">${role}</span>`;
        
        // Estado
        const tdEstado = document.createElement('td');
        const estado = info.estado || 'offline';
        
        let estadoTexto, estadoClase;
        switch(estado) {
            case 'online':
                estadoTexto = '🟢 Online';
                estadoClase = 'estado-online';
                break;
            case 'registrado':
                estadoTexto = '🟡 Registrado';
                estadoClase = 'estado-registrado';
                break;
            case 'desconectado':
                estadoTexto = '🔴 Desconectado';
                estadoClase = 'estado-desconectado';
                break;
            default:
                estadoTexto = '⚪ Offline';
                estadoClase = 'estado-offline';
        }
        
        tdEstado.innerHTML = `<span class="${estadoClase}">${estadoTexto}</span>`;
        
        // Actividad (NUEVO)
        const tdActividad = document.createElement('td');
        tdActividad.className = 'text-center';
        const actividad = info.actividad || 'Unknown';
        tdActividad.innerHTML = `<span class="badge bg-success">${actividad}</span>`;
        
        tr.appendChild(tdId);
        tr.appendChild(tdNombre);
        tr.appendChild(tdGrupo);
        tr.appendChild(tdRole);
        tr.appendChild(tdEstado);
        tr.appendChild(tdActividad);
        
        tbody.appendChild(tr);
    });
}

function actualizarEstadisticas() {
    const total = Object.keys(state.dispositivos).length;
    const conectados = Object.values(state.dispositivos).filter(d => d.estado === 'online').length;
    
    const statsText = document.getElementById('stats-text');
    statsText.textContent = `Total: ${total} alumnos / ${conectados} conectados`;
}

// ============================================================================
// FUNCIONES UI - PANEL PREGUNTA
// ============================================================================

function mostrarPanelPregunta(pregunta) {
    const panel = document.getElementById('pregunta-panel');
    panel.classList.remove('d-none');
    
    const infoEl = document.getElementById('pregunta-info');
    infoEl.innerHTML = `<strong>Pregunta #${pregunta.index}:</strong> ${pregunta.tipo} con ${pregunta.num_opciones} opciones`;
    
    const lista = document.getElementById('respuestas-list');
    lista.innerHTML = '';
    
    Object.entries(state.dispositivos).forEach(([device_id, info]) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.id = `respuesta-${device_id}`;
        
        const nombre = info.nombre || device_id.substring(0, 8);
        const grupo = info.grupo || '?';
        const role = info.role || '?';
        
        li.innerHTML = `
            <span>${nombre} <small class="text-muted">[G${grupo}:${role}]</small></span>
            <span class="badge bg-secondary">Esperando...</span>
        `;
        
        lista.appendChild(li);
    });
    
    actualizarCountdown(pregunta.timeout || 30);
}

function actualizarCountdown(segundos) {
    const countdownEl = document.getElementById('countdown-info');
    
    if (segundos > 0) {
        countdownEl.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-warning text-dark">${segundos}s</span>`;
    } else {
        countdownEl.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-danger">Completo</span>`;
    }
}

function actualizarRespuestaEnLista(device_id, nombre, respuesta) {
    const li = document.getElementById(`respuesta-${device_id}`);
    
    if (li) {
        const badgeSpan = li.querySelector('.badge');
        badgeSpan.textContent = respuesta || '(vacía)';
        badgeSpan.className = 'badge bg-success';
    }
}

function ocultarPanelPregunta() {
    const panel = document.getElementById('pregunta-panel');
    panel.classList.add('d-none');
    state.preguntaActiva = null;
}

// ============================================================================
// EVENT LISTENERS - BOTONES
// ============================================================================

// Guardar TODO
// GUARDAR: Descargar archivo CSV
document.getElementById('guardar-todo-btn').addEventListener('click', async () => {
    const url = document.getElementById('url-input').value.trim();
    const pin = document.getElementById('pin-input').value.trim();
    const timeout = parseInt(document.getElementById('timeout-input').value);
    const nombreArchivo = document.getElementById('nombre-archivo-input').value.trim();

    if (!url || !pin) {
        alert('Por favor completa URL y PIN');
        return;
    }

    if (!nombreArchivo) {
        alert('Por favor ingresa un nombre para el archivo');
        return;
    }

    try {
        agregarLog('INFO', `Generando archivo: ${nombreArchivo}.csv`);

        const response = await fetch('/api/guardar_todo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                pin,
                timeout,
                nombre_archivo: nombreArchivo,
                alumnos: Object.entries(state.dispositivos).map(([id, info]) => ({
                    id: id,
                    nombre: info.nombre || '',
                    grupo: info.grupo || '',
                    role: info.role || ''
                }))
            })
        });

        if (response.ok) {
            // Descargar archivo
            const blob = await response.blob();
            const downloadUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${nombreArchivo}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            
            // Guardar último nombre en localStorage
            localStorage.setItem('ultimo_archivo', nombreArchivo);
            
            agregarLog('INFO', `✅ Archivo descargado: ${nombreArchivo}.csv`);
            alert(`✅ Archivo descargado exitosamente:
${nombreArchivo}.csv`);
        } else {
            const data = await response.json();
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error guardando:', error);
        agregarLog('ERROR', `Error guardando: ${error.message}`);
        alert('❌ Error generando archivo');
    }
});

// ⭐ Conectar a ClassQuiz (con desconexión previa automática)
document.getElementById('conectar-classquiz-btn').addEventListener('click', async () => {
    // Leer valores actuales
    const url = document.getElementById('url-input').value.trim();
    const pin = document.getElementById('pin-input').value.trim();
    const timeout = parseInt(document.getElementById('timeout-input').value);

    // Validaciones
    if (!url || !pin) {
        alert('Por favor completa URL y PIN en la pestaña Configuración');
        agregarLog('ERROR', 'URL o PIN faltante');
        return;
    }

    if (isNaN(timeout) || timeout < 5 || timeout > 300) {
        alert('Timeout debe estar entre 5 y 300 segundos');
        agregarLog('ERROR', 'Timeout inválido');
        return;
    }

    const numDispositivos = Object.keys(state.dispositivos).length;
    if (numDispositivos === 0) {
        alert('⚠️ No hay dispositivos detectados.\n\nPresiona "Descubrir Dispositivos" primero.');
        agregarLog('ERROR', 'No hay dispositivos para conectar');
        return;
    }

    // Confirmar reconexión
    const confirmar = confirm(
        `🔄 RECONEXIÓN A CLASSQUIZ\n\n` +
        `Se desconectará la sesión anterior y se conectarán ${numDispositivos} dispositivo(s) con:\n\n` +
        `📍 URL: ${url}\n` +
        `🔑 PIN: ${pin}\n` +
        `⏱️ Timeout: ${timeout}s\n\n` +
        `¿Continuar?`
    );

    if (!confirmar) {
        agregarLog('INFO', 'Conexión cancelada por el usuario');
        return;
    }

    agregarLog('INFO', `🔄 Iniciando reconexión a ${url} (PIN: ${pin})...`);

    const statusAlert = document.getElementById('status-conexion-alert');
    const statusTexto = document.getElementById('status-conexion-texto');
    statusAlert.classList.remove('d-none');
    statusTexto.textContent = '🔄 Preparando reconexión...';
    statusAlert.className = 'alert alert-info mt-3';

    try {
        // ⭐ El backend automáticamente desconecta la sesión anterior
        const response = await fetch('/api/conectar_classquiz', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                pin: pin,
                timeout: timeout
            })
        });

        const data = await response.json();

        if (response.ok && data.status === 'ok') {
            agregarLog('INFO', `✅ Reconexión iniciada para ${data.count} dispositivo(s)`);
            agregarLog('INFO', `📍 URL: ${url} | PIN: ${pin}`);
            statusTexto.textContent = `✅ ${data.count} dispositivo(s) conectándose con PIN ${pin}...`;
            statusAlert.className = 'alert alert-success mt-3';

            setTimeout(() => {
                statusAlert.classList.add('d-none');
            }, 5000);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error conectando a ClassQuiz:', error);
        agregarLog('ERROR', `Error conectando: ${error.message}`);
        statusTexto.textContent = `❌ ${error.message}`;
        statusAlert.className = 'alert alert-danger mt-3';
    }
});

// Descubrir dispositivos
document.getElementById('descubrir-btn').addEventListener('click', async () => {
    agregarLog('INFO', 'Iniciando descubrimiento de dispositivos...');
    
    try {
        const response = await fetch('/api/descubrir', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            agregarLog('INFO', 'Comando de descubrimiento enviado');
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error en descubrimiento:', error);
        agregarLog('ERROR', `Error en descubrimiento: ${error.message}`);
    }
});

// Cargar configuración
// CARGAR: Upload de archivo CSV
document.getElementById('cargar-config-btn').addEventListener('click', () => {
    // Crear input file dinámicamente
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.csv';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        agregarLog('INFO', `Cargando archivo: ${file.name}`);
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/api/cargar_config', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'ok') {
                // Actualizar campos con datos cargados
                if (data.url) document.getElementById('url-input').value = data.url;
                if (data.pin) document.getElementById('pin-input').value = data.pin;
                if (data.timeout) document.getElementById('timeout-input').value = data.timeout;
                
                // Extraer nombre base del archivo (sin .csv)
                const nombreBase = file.name.replace('.csv', '');
                document.getElementById('nombre-archivo-input').value = nombreBase;
                
                // Guardar en localStorage
                localStorage.setItem('ultimo_archivo', nombreBase);
                
                agregarLog('INFO', `✅ Cargado: ${file.name}`);
                agregarLog('INFO', `Config cargada + ${data.alumnos_cargados || 0} alumnos`);
                alert(`✅ Archivo cargado exitosamente:
${file.name}

Config + ${data.alumnos_cargados || 0} alumnos`);
            } else {
                throw new Error(data.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('Error cargando config:', error);
            agregarLog('ERROR', `Error cargando: ${error.message}`);
            alert(`❌ Error cargando archivo:
${error.message}`);
        }
    };
    
    // Trigger file dialog
    input.click();
});

// Finalizar votación
document.getElementById('finalizar-btn').addEventListener('click', () => {
    if (confirm('¿Finalizar votación ahora?')) {
        socket.emit('finalizar_votacion');
        agregarLog('INFO', 'Votación finalizada manualmente');
        ocultarPanelPregunta();
    }
});

// Toggle DEBUG
document.getElementById('debug-checkbox').addEventListener('change', (e) => {
    state.debugVisible = e.target.checked;
    refrescarLogs();
    agregarLog('INFO', `Logs DEBUG ${state.debugVisible ? 'activados' : 'desactivados'}`);
});

// Exportar logs
document.getElementById('exportar-btn').addEventListener('click', () => {
    const texto = state.logs.map(log => `[${log.timestamp}] [${log.nivel}] ${log.msg}`).join('\n');
    
    const blob = new Blob([texto], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().replace(/:/g, '-')}.txt`;
    a.click();
    
    URL.revokeObjectURL(url);
    
    agregarLog('INFO', 'Logs exportados a archivo');
});

// ============================================================================
// AUTO-SCROLL PAUSABLE
// ============================================================================

let pauseTimeout = null;

document.getElementById('log-container').addEventListener('click', () => {
    const container = document.getElementById('log-container');
    
    state.autoScroll = false;
    container.classList.add('paused');
    
    if (pauseTimeout) {
        clearTimeout(pauseTimeout);
    }
    
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
    
    // Cargar último nombre de archivo desde localStorage
    const ultimoArchivo = localStorage.getItem('ultimo_archivo');
    if (ultimoArchivo) {
        document.getElementById('nombre-archivo-input').value = ultimoArchivo;
        agregarLog('INFO', `Último archivo recordado: ${ultimoArchivo}.csv`);
    }
    
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.url) document.getElementById('url-input').value = data.url;
        if (data.pin) document.getElementById('pin-input').value = data.pin;
        if (data.timeout) document.getElementById('timeout-input').value = data.timeout;
        
    } catch (error) {
        console.error('Error cargando config inicial:', error);
    }
});

// ============================================================================
// BÚSQUEDA EN LOGS
// ============================================================================

document.getElementById('buscar-input').addEventListener('input', (e) => {
    const busqueda = e.target.value.toLowerCase();
    const items = document.querySelectorAll('.log-item');
    
    items.forEach(item => {
        const texto = item.textContent.toLowerCase();
        item.style.display = texto.includes(busqueda) ? 'block' : 'none';
    });
});