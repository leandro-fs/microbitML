---
title: microbitML
description: Framework de comunicación radio y persistencia para BBC micro:bit con MicroPython
---

# microbitML

Framework para actividades educativas grupales con BBC micro:bit V2 y MicroPython.

Los micro:bits se comunican por radio y se agrupan en equipos. Dentro de cada equipo, cada dispositivo asume un rol diferente. Todo el aula comparte el mismo canal de radio, permitiendo también un nodo docente/monitor.

---

## Actividades disponibles

| Actividad | Descripción | micro:bits necesarios |
|---|---|---|
| [mbClassquiz](actividades/mbclassquiz/README.md) | Integración con la plataforma ClassQuiz para quizzes interactivos | 1 concentrador + N alumnos |
| [mbContador](actividades/mbcontador/README.md) | Contador distribuido en base N — práctica de sistemas de numeración | 2 a 26 (uno por dígito) |
| [mbPerceptron](actividades/mbperceptron/README.md) | Perceptrón distribuido — introducción a Machine Learning | 3 (roles A, B, Z) |
| [mbSnake](actividades/mbsnake/README.md) | Juego de la viborita en la matriz de LEDs 5×5 | 2 |

---

## Guías

- [Instalación de Microbit-ClassQuiz](guias/instalacion_microbit_classquiz.md) — Editor web + programa PC
- [Instalación de ClassQuiz (servidor)](guias/instalacion_classquiz.md) — Docker self-hosted
- [Gmail SMTP](guias/smtp_gmail.md) — Contraseña de aplicación para emails
- [Configuración de roles y grupos](guias/configuracion.md) — Pin1 + botones físicos
- [Carga de firmware](guias/carga_firmware.md) — Editor web y archivos .hex

---

## Framework

- [Guía de uso de microbitml](framework/guia_microbitml.md) — Radio, mensajes, ConfigManager

---

Licencia GPLv3
(c) 2026 - [Fundación Sadosky](https://fundacionsadosky.org.ar/)