# Contribuir a microbitML

¡Gracias por tu interés! microbitML recibe contribuciones de personas con perfiles muy distintos.

Para guías detalladas, ver la [documentación de contribuciones](docs/contributing/).

---

## Perfiles de contribución

| Tu perfil | Qué podés aportar |
|---|---|
| **Docente / redactor/a** | Nuevas actividades pedagógicas, mejoras a la documentación, reportes de uso real en clase |
| **Desarrollador/a Python** | Nuevas actividades de firmware, mejoras al framework `microbitml.py`, mejoras a la app de escritorio |
| **Diseñador/a de hardware** | Shields, módulos de expansión u otros diseños físicos complementarios para micro:bit |

## Proceso

1. Hacé un **fork** del repositorio
2. Creá una **rama** descriptiva (`feat/nueva-actividad`, `fix/serial-timeout`, `docs/guia-sensores`)
3. Abrí un **Pull Request** describiendo qué cambia y por qué

## Firmware y hardware físico

microbitML genera actividades que involucran hardware real: sensores, actuadores y la
propia placa micro:bit. Antes de abrir un PR con cambios de firmware:

- **Probá en hardware real.** No existe suite de pruebas automatizadas; la validación es manual.
- Si la actividad usa periféricos adicionales (sensores, servos, pantallas), documentá el circuito
  en el README de la actividad.
- Si contribuís un **diseño de hardware** (PCB, esquemático, archivos KiCad), se aplica la
  licencia CERN-OHL-S v2 (ver tabla de licencias más abajo).

## Licencias

Al contribuir aceptás que tu aporte queda bajo las licencias vigentes:

| Tipo de contribución | Licencia |
|---|---|
| Código fuente (`.py`, `.js`, etc.) | [GPLv3](LICENSE) |
| Documentación (archivos `.md`, guías) | [CC BY-SA 4.0](LICENSE-docs) |
| Diseños de hardware (PCB, KiCad, esquemáticos) | CERN-OHL-S v2 |

Para la escala actual del proyecto se presume licencia por acto de contribución (sin CLA/DCO).
Si el proyecto escala, se evaluará implementar un [DCO](https://developercertificate.org/).

## Código de conducta y salvaguarda de menores

Este proyecto sigue el [Código de Conducta](CODE_OF_CONDUCT.md) basado en el
Contributor Covenant 2.1. Al participar, te comprometés a respetarlo.

microbitML se usa en entornos educativos con estudiantes menores de edad. Los principios
de protección de menores son consistentes con la
[Safeguarding Policy](https://microbit.org/safeguarding/) de la Micro:bit Educational
Foundation. En particular:

- Los espacios del proyecto deben ser aptos para  menores 
- En canales en línea, preferir la comunicación pública; evitar mensajes directos no solicitados.
- Incidentes de salvaguarda pueden reportarse a [safeguarding@microbit.org](mailto:safeguarding@microbit.org).

Las contribuciones de firmware que usen sensores, actuadores u otros periféricos físicos
en contextos escolares deben documentar las precauciones de seguridad pertinentes en el
README de la actividad.
