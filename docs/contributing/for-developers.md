---
title: Contribuir (para desarrolladores/as)
---

# Contribuir (para desarrolladores/as)

## Stack del proyecto

| Capa | Tecnología | Dónde está |
|---|---|---|
| Firmware micro:bit | MicroPython | `microbitml.py`, `mb*/` |
| App de escritorio | Python + Flask/SocketIO + Tkinter | `mbClassquiz/Interface_grafica/` |
| Documentación | MkDocs Material + `properdocs` | `docs/`, `mkdocs.yml` |

## Entorno de desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/leandro-fs/microbitML
cd microbitML

# App de escritorio
cd mbClassquiz/Interface_grafica
pip install -r requirements.txt
python main.py

# Documentación
cd ../..
pip install -r docs-requirements.txt
properdocs serve   # → http://127.0.0.1:8000
```

## Firmware y hardware físico

`microbitml.py` es **MicroPython** que corre en el micro:bit, no en CPython.
Esto tiene implicancias concretas para contribuir:

- **No hay suite de pruebas automatizadas.** La validación es manual con hardware real.
- **Probá en dispositivo antes de abrir el PR.** Los errores de MicroPython (memoria,
  imports no disponibles, radio) solo se manifiestan en el hardware.
- Si la actividad usa **sensores o actuadores** (servos, LEDs externos, sensores I²C/SPI):
  - Documentá el circuito en el README de la actividad con un diagrama o esquemático.
  - Indicá los límites de voltaje/corriente seguros para el contexto escolar.
  - Avisá si el sensor requiere alimentación externa (3V vs 5V).
  - Recordá que el hardware lo manipulan estudiantes de entre 10 y 18 años bajo supervisión
    docente: evitá diseños con partes cortantes, superficies calientes o tensiones peligrosas
    sin aislamiento adecuado. Ver [Safeguarding Policy](https://microbit.org/safeguarding/).
- `mkdocstrings` **no puede analizar** `microbitml.py` ni ningún firmware de actividad:
  importan módulos MicroPython (`from microbit import ...`) que no existen en CPython.
  No hay auto-generación de API docs.

## Diseños de hardware

Si contribuís un diseño de hardware (shield para micro:bit, módulo de expansión, PCB):

- Usá la licencia **CERN-OHL-S v2** (copyleft fuerte equivalente a GPLv3 para hardware).
- Incluí los archivos fuente editables (KiCad, no solo Gerbers).
- Declaralo explícitamente en el README de la actividad correspondiente.

> [!note] ¿Por qué CERN-OHL-S y no GPLv3 para hardware?
> GPLv3 fue diseñada para software y deja zonas grises al aplicarse a diseños físicos
> (fabricación, producto terminado, atribución en el objeto). CERN-OHL-S v2 cubre
> esos casos explícitamente. Ver [cern-ohl.web.cern.ch](https://cern-ohl.web.cern.ch/).

## Agregar una nueva actividad

Una actividad típica tiene esta estructura:

```
mbNuevaActividad/
├── nueva_actividad.py     # Firmware nodo estudiante (MicroPython)
├── concentrador.py        # Firmware concentrador, si aplica (MicroPython)
├── nueva_actividad.hex    # Precompilado flasheable directamente
├── concentrador.hex       # Precompilado del concentrador, si aplica
└── README.md              # Descripción pedagógica y técnica
```

Si la actividad tiene interfaz de escritorio, sigue el patrón
`Registry + MVC` de `mbClassquiz/Interface_grafica/` (ver `CLAUDE.md`).

## Agregar una página de documentación

1. Crear el `.md` en el subdirectorio apropiado de `docs/`
2. Agregarlo a la sección `nav:` en `mkdocs.yml`
3. Verificar con `properdocs serve` que no hay links rotos

## Compatibilidad Obsidian

La carpeta `docs/` está diseñada para abrirse como vault de Obsidian por colaboradores
no técnicos. Por favor:

- No agregues archivos a `docs/` que rompan la estructura del vault
- No uses sintaxis que solo se renderice en MkDocs pero se vea rota en Obsidian
- Mantené `docs/.obsidian/` en el gitignore
- Verificá que tus cambios se rendericen bien tanto en `properdocs serve` como en Obsidian

## Licencia del código

El código de este proyecto está bajo [GPLv3](../../LICENSE).
Al contribuir, aceptás que tu aporte se publique bajo esa licencia.
