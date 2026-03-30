---
title: Gmail - Contraseña de aplicación para SMTP
description: Cómo generar una contraseña de aplicación de Gmail para configurar el envío de emails
---

# Gmail: Contraseña de aplicación para SMTP

Requisito previo para configurar el envío de emails en ClassQuiz y otros servicios.

---

## 1. Activar verificación en 2 pasos

Ir a: [https://support.google.com/accounts/answer/185839](https://support.google.com/accounts/answer/185839)

Seguir las instrucciones de Google para activar la verificación en dos pasos en tu cuenta.

!!! warning
    Sin la verificación en 2 pasos activada, Google no permite generar contraseñas de aplicación.

---

## 2. Generar contraseña de aplicación

Ir a: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

1. Ingresar un nombre descriptivo (ej: `ClassQuiz SMTP`)
2. Hacer clic en **Crear**
3. Google genera una contraseña de 16 caracteres con formato: `xxxx xxxx xxxx xxxx`
4. Copiar y guardar la contraseña — **no se puede volver a ver**

---

## 3. Verificar que funciona (opcional)

Usar el test online: [https://www.gmass.co/smtp-test](https://www.gmass.co/smtp-test)

| Campo | Valor |
|---|---|
| SMTP Server | `smtp.gmail.com` |
| Port | `587` |
| Username | tu email de Gmail |
| Password | la contraseña de app sin espacios |

---

## Datos SMTP para ClassQuiz

Estos son los valores a usar en `docker-compose.yml`:

```yaml
MAIL_PORT: "587"
MAIL_ADDRESS: "tu_email@gmail.com"
MAIL_PASSWORD: "xxxx xxxx xxxx xxxx"   # Con espacios
MAIL_USERNAME: "tu_email@gmail.com"
MAIL_SERVER: "smtp.gmail.com"
```

---

## Test rápido desde Python

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

servidor_smtp = 'smtp.gmail.com'
puerto_smtp = 587
usuario = 'tu_email@gmail.com'
contrasena = 'xxxx xxxx xxxx xxxx'  # Contraseña de aplicación
destinatario = 'destinatario@ejemplo.com'

email = MIMEMultipart()
email['From'] = usuario
email['To'] = destinatario
email['Subject'] = 'Test SMTP'
email.attach(MIMEText('Si recibís esto, el SMTP funciona.', 'plain'))

with smtplib.SMTP(servidor_smtp, puerto_smtp) as srv:
    srv.starttls()
    srv.login(usuario, contrasena)
    srv.sendmail(usuario, destinatario, email.as_string())
    print("Correo enviado")
```