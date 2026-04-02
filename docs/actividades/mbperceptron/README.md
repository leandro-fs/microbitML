---
title: mbPerceptron
description: Perceptrón distribuido con micro:bits — introducción a Machine Learning
---

# mbPerceptron — Inteligencia Artificial con micro:bits

Actividad educativa para BBC micro:bit basada en la biblioteca [microbitML](https://github.com/leandro-fs/microbitML).

Esta actividad inspiró la creación del framework en 2024. Su nombre, `microbitML`, responde a que se pensó originalmente para explorar conceptos de Machine Learning en el aula. Complementa las funcionalidades de [Micro:bit CreateAI](https://createai.microbit.org/), pudiendo servir como introducción al tema "modelos de ML", para luego entrenar modelos con CreateAI.

---

## ¿Qué práctica aplica esta actividad?

Un **perceptrón distribuido**: varios micro:bits trabajan en conjunto para simular la neurona artificial más simple del Machine Learning. Sin decirles qué tienen entre manos, los estudiantes infieren por interacción directa —y debate grupal— cuál es la operación matemática subyacente. Luego el docente introduce la jerga de Machine Learning sobre lo que los estudiantes ya descubrieron.

---

## ¿Cuántos micro:bits se necesitan?

**3 por grupo** (roles A, B y Z). Pueden formarse varios grupos simultáneamente en el aula; cada uno trabaja en su propio canal de grupo sin interferir con los demás.

| Rol | Función | Valores posibles |
|-----|---------|-----------------|
| A | Entrada / dendrita — envía un conteo multiplicado por **1** | {0, 1, 2, 3} |
| B | Entrada / dendrita — envía un conteo multiplicado por **2** | {0, 2, 4, 6} |
| Z | Salida / axón — suma A y B y aplica una función de activación binaria (verdadero si la suma supera 6) | barra vertical encendida / apagada |

Todos los micro:bits ejecutan el mismo programa. Lo único que los diferencia es el rol y el grupo configurados en cada uno.

---

## Cómo usar la actividad

### 1. Cargar el programa

Cargar `perceptron.hex` (drag & drop) en cada micro:bit, o cargar `perceptron.py` junto con `microbitml.py` usando el [editor oficial](https://python.microbit.org/v/3). El código no es compatible con MakeCode.

### 2. Configurar rol y grupo en cada micro:bit

**Para entrar al modo configuración:** mantener el Pin1 conectado a GND con un cable y presionar los botones:

| Acción | Efecto |
|--------|--------|
| Pin1 + Botón A | Cambia al siguiente rol (A → B → Z) |
| Pin1 + Botón B | Cambia al siguiente grupo (1 → 2 … 9) |
| Tocar el logo (sin botones) | Muestra el rol y grupo actuales (ej. A1, B2) |

`microbitML` guarda automáticamente la configuración y la recuerda aunque se apague el dispositivo. Evitar el grupo 0: cualquier nodo que se reinicie sin configuración previa vuelve a ese grupo.

### 3. Operar la actividad

- En los micro:bits con rol A y B: el **Botón A** incrementa el conteo, el **Botón B** lo decrementa.
- El micro:bit Z muestra una barra vertical encendida cuando la suma supera el umbral; apagada cuando no.
- El rol Z actualiza su pantalla automáticamente cada vez que recibe un mensaje de A o B.

---

## Sugerencia de dinámica de clase

### Fase 1 — Exploración libre

Entregar los micro:bits sin explicar qué hacen. Plantear las preguntas:

1. ¿Qué **dos** operaciones matemáticas gobiernan la barra vertical en Z? *(respuesta: suma A y B, luego compara con 6)*
2. ¿Cuál es la diferencia entre A y B? *(A multiplica su conteo por 1; B por 2)*

Dar tiempo a que cada grupo interactúe con los dispositivos y debata hasta llegar a una hipótesis.

### Fase 2 — Introducción al vocabulario de ML

Una vez que los grupos infirieron las respuestas, el docente puede introducir los siguientes conceptos:

- Los micro:bits A, B y Z forman un **perceptrón**: la unidad básica de procesamiento en Machine Learning.
- A y B almacenan distintos **pesos** (*weights*), que constituyen un **modelo de ML** (*ML model*).
- Z suma las entradas ponderadas y aplica una **función de activación** (*activation function*). Su salida puede ser una **clasificación** final, o bien alimentar hacia adelante (*feed forward*) otra **capa** (*layer*) de perceptrones en un **MLP**. Z puede también aplicar un **sesgo** (*bias*).
- Los *pesos* son fijos en esta demo, pero la parte "Learning" del **ML Supervisado** (*Supervised ML*) consiste en ajustarlos mediante miles de ciclos de exposición a **muestras etiquetadas** que forman un **dataset**. Eso se llama **entrenamiento** (*training*).
- Como parte del *pipeline*, el *modelo* se **valida** contra un *dataset* completamente nuevo. Si las métricas se mantienen, el modelo se considera listo para producción.
- **Conclusión para el aula:** al consumir dispositivos con ML incorporado, siempre tener en cuenta que los errores de clasificación van a ocurrir, especialmente si el *modelo* no fue entrenado para la aplicación en cuestión.

---

## Estructura de archivos

```
mbPerceptron/
├── perceptron.py      ← Código fuente (MicroPython)
├── perceptron.hex     ← Firmware precompilado
└── README.md

microbitml.py          ← Biblioteca compartida (cargar junto con perceptron.py)
```

---

Basado en el artículo del Prof. Fujio Yamamoto: [building a Microbit network emulating a MLP](https://sparse-dense.blogspot.com/2018/06/microbittwo-layer-perceptronxor.html).

Licencia GPLv3  
(C) 2024–2025 [Leandro Batlle](https://www.linkedin.com/in/lean-b/) — Área de Innovación Educativa Científico-Tecnológica, [Colegio Nacional de Buenos Aires](https://www.cnba.uba.ar)  
(C) 2025 [Fundación Sadosky](https://fundacionsadosky.org.ar/)
