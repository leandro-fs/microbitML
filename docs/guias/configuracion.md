---
title: Configuración de roles y grupos
description: Cómo configurar rol y grupo en cada micro:bit usando los botones físicos
---

# Configuración de roles y grupos

Cada micro:bit necesita saber qué **rol** tiene y a qué **grupo** pertenece. El rol determina la función del dispositivo dentro de la actividad, y el grupo permite que varios equipos trabajen simultáneamente en el aula sin interferirse.

---

## Conceptos

**Rol:** Identifica la función del micro:bit dentro de la actividad. Por ejemplo, en mbContador los roles `A`, `B`, `C` representan los dígitos del número. En mbClassquiz los roles identifican a cada alumno dentro de un grupo.

**Grupo:** Identifica al equipo o mesa de trabajo. Los micro:bits del mismo grupo se comunican entre sí. El grupo `0` es broadcast (llega a todos).

---

## Método de configuración

La configuración se realiza exclusivamente con los **botones físicos** del micro:bit. No se configura desde la PC.

### Requisitos

- Un cable cocodrilo o jumper conectando **Pin1 a GND**

### Pasos

1. Conectar Pin1 a GND con un cable cocodrilo
2. Mientras Pin1 está conectado a GND:

| Acción | Efecto |
|---|---|
| Presionar **Botón A** | Cambia al siguiente rol (A → B → C → ... → A) |
| Presionar **Botón B** | Cambia al siguiente grupo (1 → 2 → ... → 9 → 1) |

3. Desconectar el cable de Pin1 para salir del modo configuración

!!! tip
    Para ver la configuración actual sin modificarla, tocar el **logo** (la cara dorada entre los LEDs) del micro:bit. Se mostrará primero el rol y luego el grupo en la pantalla de LEDs.

---

## Persistencia

La configuración se guarda automáticamente en la memoria flash del micro:bit cada vez que se modifica un valor. Esto significa que:

- La configuración **sobrevive** si se desconecta la alimentación o se reinicia el micro:bit
- La configuración **se pierde** si se flashea un nuevo firmware (archivo .hex)

!!! warning
    Cada vez que se carga un nuevo firmware al micro:bit, es necesario volver a configurar el rol y el grupo.

---

## Roles disponibles por actividad

Los roles dependen de la actividad cargada en el micro:bit:

| Actividad | Roles disponibles | Descripción |
|---|---|---|
| mbClassquiz | A, B, C, D, E, Z | Alumnos (A-E) y concentrador (Z) |
| mbContador | A, B, C, ... | Cada rol es un dígito del contador |
| mbPerceptron | Z, A, B | Z es el axón, A y B son entradas |
| mbSnake | A, B | Jugadores |

---

## Grupos

El rango de grupos es configurable por actividad, pero por defecto va de **1 a 9**. El grupo determina qué micro:bits se comunican entre sí por radio.

!!! note
    Los mensajes enviados desde el grupo `0` son recibidos por todos los grupos (broadcast). Los micro:bits normales nunca deben configurarse en grupo 0.

---

## Ejemplo práctico

Para configurar un micro:bit como **Rol B, Grupo 3**:

1. Conectar Pin1 a GND con cable cocodrilo
2. Presionar **Botón A** una vez (pasa de A a B)
3. Presionar **Botón B** tres veces (pasa de 1 a 2, de 2 a 3)
4. Verificar tocando el logo: debe mostrar `B` y luego `3`
5. Desconectar el cable de Pin1

---

## Solución de problemas

**El micro:bit no responde a los botones en modo configuración:**
Verificar que Pin1 esté efectivamente conectado a GND. El contacto debe ser firme. El modo capacitivo (tocar con el dedo) no funciona para esta operación.

**El rol o grupo vuelve al valor anterior:**
Esto no debería pasar ya que `config_rg()` guarda automáticamente. Si ocurre, verificar que la memoria flash no esté llena o corrupta. Flashear nuevamente el firmware y reconfigurar.

**Después de flashear, el micro:bit arranca con rol A grupo 1:**
Es el comportamiento esperado. Flashear un nuevo firmware borra la configuración guardada. Volver a configurar rol y grupo.