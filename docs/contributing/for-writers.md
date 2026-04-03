---
title: Contribuir con documentación (para redactores/as)
---

# Contribuir con documentación

No necesitás saber programar para contribuir a la documentación de microbitML.
Alcanza con tener [Obsidian](https://obsidian.md) (gratuito) y una cuenta en GitHub.

## Configuración (una sola vez, ~5 minutos)

1. Hacé un **fork** del repositorio en GitHub
2. **Cloná** el repositorio a tu computadora
3. Abrí la carpeta `docs/` como **vault de Obsidian**
   (`Archivo → Abrir vault → Abrir carpeta como vault → seleccioná docs/`)
4. En Obsidian, andá a `Configuración → Archivos y enlaces`:
    - **Desactivá** `Usar [[Wikilinks]]` → usá links Markdown estándar
    - **Formato de nuevos links** → `Ruta relativa al archivo`

> [!tip] ¿Por qué desactivar los wikilinks?
> Los links Markdown estándar (`[texto](archivo.md)`) funcionan en todas partes:
> en Obsidian, en GitHub y en el sitio publicado.
> Los wikilinks (`[[archivo]]`) solo funcionan en Obsidian.

## ¿Qué podés contribuir?

- **Actividades pedagógicas nuevas** — usá la plantilla en `docs/_templates/plantilla-readme-actividad.md`
- **Mejoras a guías existentes** — correcciones, aclaraciones, imágenes, ejemplos
- **Reportes de uso real** — qué funcionó y qué no en clase, con qué edades, con qué variantes
- **Traducciones** — la documentación está en español; si hay contenido en otro idioma, se acepta traducción

## Convenciones de escritura

### Lo que podés usar libremente

Estas funciones funcionan igual en Obsidian y en el sitio publicado:

- **Títulos** (`# H1` hasta `#### H4`)
- **Negrita**, *cursiva*, ~~tachado~~, ==resaltado==
- Links Markdown estándar: `[texto](otra-pagina.md)`
- Imágenes: `![alt](../assets/imagen.png)`
- Bloques de código con resaltado de sintaxis
- Tablas
- Listas de tareas (`- [ ] pendiente`)
- Diagramas Mermaid (dentro de bloques ` ```mermaid `)
- Callouts / admonitions:

```text
> [!note] Título acá
> Texto del cuerpo acá.
>
> Soporta **formato** y `código`.
```

Tipos de callout disponibles: `note`, `tip`, `warning`, `danger`, `example`,
`question`, `quote`, `info`, `bug`, `success`, `failure`, `abstract`.

### Qué evitar

| Función | Por qué | Alternativa |
|---|---|---|
| `[[wikilinks]]` | No es portable | `[texto](archivo.md)` |
| `![[embed]]` | No es portable | Copiá el texto relevante o vinculá |
| `^referencias-de-bloque` | No es portable | Usá links a encabezados: `[texto](archivo.md#encabezado)` |
| Plugins exclusivos de Obsidian | No se renderizan en el sitio | Usá Markdown estándar |

## Cómo enviar tus cambios

1. Creá una **rama** nueva para tus cambios (`docs/nombre-descriptivo`)
2. Escribí o editá archivos `.md` dentro de `docs/`
3. Hacé **commit** y **push** a tu fork
4. Abrí un **Pull Request** en GitHub describiendo qué cambiaste y por qué

> [!tip] Vista previa antes de enviar
> Podés ver cómo quedarán los docs en el sitio pidiendo a alguien técnico que ejecute
> `properdocs serve` localmente, o revisando el preview de ReadTheDocs en el PR.

## Contenido apto para menores

microbitML está dirigido a estudiantes de entre 10 y 18 años. Toda la documentación
que contribuyas debe ser apta para ese rango etario:

- Lenguaje claro, sin jerga ofensiva ni contenido inapropiado para menores
- Imágenes y ejemplos adecuados para contextos escolares
- Si describís una actividad con hardware, incluí las precauciones de seguridad pertinentes

Esta política es consistente con la [Safeguarding Policy](https://microbit.org/safeguarding/)
de la Micro:bit Educational Foundation.

## Licencia de las contribuciones

La documentación de este proyecto está bajo [CC BY-SA 4.0](../../LICENSE-docs).
Al contribuir, aceptás que tu aporte se publique bajo esa licencia.
