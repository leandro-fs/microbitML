---
title: Instalación de ClassQuiz
description: Instalación del servidor ClassQuiz self-hosted con Docker en Windows
---

# Instalación de ClassQuiz (servidor)

ClassQuiz es la plataforma web de quizzes interactivos que se integra con los micro:bits. Esta guía cubre la instalación self-hosted en Windows usando Docker.

!!! note
    Esta guía es para instalar el **servidor ClassQuiz** (la plataforma web). Para instalar el **programa PC** que conecta los micro:bits con ClassQuiz, ver [Instalación de Microbit-ClassQuiz](instalacion_microbit_classquiz.md).

---

## Prerrequisitos

| Requisito | Detalle |
|---|---|
| Windows | 10 u 11 |
| Docker Desktop | Instalado y ejecutándose |
| Git | Instalado ([git-scm.com](https://git-scm.com)) |
| PowerShell | 5.1+ (incluido en Windows) |
| Gmail | Cuenta con contraseña de aplicación generada (ver [guía SMTP](smtp_gmail.md)) |

---

## 1. Clonar repositorio

```powershell
cd "D:\Fundacion Sadosky"
git clone https://github.com/mawoka-myblock/ClassQuiz.git
cd ClassQuiz
git checkout -b fix/windows-docker-setup
```

---

## 2. Ejecutar script de setup

El script `setup.ps1` automatiza todas las modificaciones necesarias:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

El script realiza automáticamente:

1. Agrega `asyncpg` al Pipfile y `psycopg2-binary` al Dockerfile
2. Actualiza Node.js de 19 a 22 en `frontend/Dockerfile`
3. Comenta la `API_URL` hardcodeada del frontend
4. Aplica el parche JWT en `hooks.server.ts` (corrige error 500 en login)
5. Corrige finales de línea CRLF → LF en `start.sh` y `prestart.sh`
6. Crea directorio `uploads/`
7. Genera una `SECRET_KEY` única de 64 caracteres
8. Configura `SECRET_KEY` en `docker-compose.yml` y `frontend/Dockerfile` (3 lugares)
9. Configura `ROOT_ADDRESS` como `http://localhost:8000`

!!! note
    El script pedirá tu email y contraseña de aplicación de Gmail para configurar el SMTP. Si no tenés, usá `SKIP_EMAIL_VERIFICATION=True` en `docker-compose.yml`.

---

## 3. Verificar configuración

```powershell
.\verify.ps1
```

Todos los checks deben mostrar ✅. Si hay algún ❌, revisar el paso indicado.

---

## 4. Compilar y ejecutar

```powershell
# Limpiar instalación previa (opcional)
docker compose down -v
docker system prune -af

# Compilar (10-15 min primera vez)
docker compose build

# Iniciar servicios
docker compose up -d
```

Esperar ~60 segundos para que todos los servicios inicien.

---

## 5. Verificar servicios

```powershell
docker compose ps
```

Todos deben mostrar estado **Up**: `api`, `db`, `frontend`, `meilisearch`, `proxy`, `redis`, `worker`.

```powershell
docker compose logs api | Select-String "Application startup complete"
docker compose logs frontend | Select-String "Listening on"
```

---

## 6. Primer uso

1. Abrir navegador (modo incógnito recomendado): **http://localhost:8000**
2. Registrar usuario (**Sign up**)
3. Verificar email si está habilitado, o acceder directamente si `SKIP_EMAIL_VERIFICATION=True`
4. Iniciar sesión — no debería haber error 500 gracias al parche JWT

---

## Parche JWT — Error 500 en login

El script de setup aplica automáticamente un parche crítico en el frontend. Si se necesita aplicar manualmente, este es el detalle.

### Problema

Al iniciar sesión, el frontend crashea con:

```
Error: Cannot read properties of null (reading 'payload')
```

### Causa

El backend genera tokens JWT y los almacena en una cookie con el valor `Bearer eyJhbG...`. La capa HTTP de Python (`SimpleCookie`) agrega comillas dobles literales al serializar el valor de la cookie. Cuando el frontend (SvelteKit/Node.js) lee la cookie, recibe `"Bearer eyJhbG..."` con las comillas incluidas. La librería `jws` de Node.js no puede decodificar un token que empieza con `"`, retorna `null`, y el código accede a `jwt.payload` sin validar — causando el crash.

### Solución

En `frontend/src/hooks.server.ts`, buscar la **línea 15** (después del `if (!access_token)` guard):

```typescript
	const jwt = jws.decode(access_token.replace('Bearer ', ''));
```

Reemplazar esa línea por este bloque:

```typescript
	// Fix: python-jose genera cookies con comillas literales que jws no tolera
	let token_sin_bearer = access_token.replace('Bearer ', '');
	if (token_sin_bearer.startsWith('"') && token_sin_bearer.endsWith('"')) {
		token_sin_bearer = token_sin_bearer.slice(1, -1);
	}
	const jwt = jws.decode(token_sin_bearer);
```

Luego, inmediatamente **antes** de la línea `if (Date.now() >= jwt.payload.exp * 1000)` (línea 17 original), agregar esta validación:

```typescript
	if (!jwt || !jwt.payload) {
		console.warn('[ClassQuiz] JWT inválido, limpiando cookie');
		event.locals.email = null;
		event.cookies.delete('access_token', { path: '/' });
		return resolve(event);
	}
```

El resto del archivo queda sin cambios.

---

## Resumen de modificaciones

| Archivo | Cambio |
|---|---|
| `Pipfile` | Agregado `asyncpg = "*"` |
| `Dockerfile` | Agregado `pip install asyncpg psycopg2-binary` |
| `frontend/Dockerfile` | Node 19 → 22, API_URL comentada, SECRET_KEY ×2 |
| `hooks.server.ts` | Parche JWT: limpieza de comillas en token |
| `docker-compose.yml` | SECRET_KEY, ROOT_ADDRESS, SMTP config |
| `start.sh`, `prestart.sh` | Conversión CRLF → LF |
| `uploads/` | Directorio creado |

!!! danger "SECRET_KEY"
    La misma SECRET_KEY debe estar en exactamente 3 lugares: `docker-compose.yml`, `frontend/Dockerfile` (etapa builder), `frontend/Dockerfile` (etapa serve). Si no coinciden, el login falla con error 500.

---

## Troubleshooting

| Problema | Solución |
|---|---|
| Error 502/503 | Esperar 60s más. El frontend tarda en iniciar. |
| Error 500 en login | Verificar que las 3 SECRET_KEY coincidan (`verify.ps1`). |
| ModuleNotFoundError | Rebuild: `docker compose build --no-cache` |
| Puerto 8000 ocupado | Cambiar el puerto en `docker-compose.yml` (proxy → ports). |
| Email no llega | Verificar credenciales SMTP o usar `SKIP_EMAIL_VERIFICATION=True`. |