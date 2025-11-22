"""
correo.py

Librería para envío de correos electrónicos mediante SMTP SSL.

Funciones:
- ValidarSintaxisEmailis_email(email): valida sintácticamente un email.
- EnviarCorreoSSL(credenciales, destinatario, asunto, mensaje, archivo, copia_oculta=True):
  envía un correo con opción de adjuntar un archivo y copia oculta al remitente.

Dependencias:
- smtplib, ssl, os, logging
- email.mime (MIMEMultipart, MIMEText, MIMEBase)
- email.encoders (encode_base64)
"""

import logging
import os
import smtplib
import ssl
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64


def ValidarSintaxisEmail(email: str) -> bool:
    """
    Valida sintácticamente un correo electrónico.

    Args:
        email (str): Dirección de correo a validar.

    Returns:
        bool: True si el email tiene sintaxis correcta, False en caso contrario.
    """
    pattern = r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$'
    match = re.match(pattern, email.lower())
    return match is not None


def EnviarCorreoSSL(
    credenciales: list,
    destinatario: str,
    asunto: str,
    mensaje: str,
    archivo: str = "",
    copia_oculta: bool = True
) -> tuple[bool, dict]:
    """
    Envía un correo electrónico usando SMTP SSL con las credenciales proporcionadas.

    Args:
        credenciales (list): [remitente, servidor_smtp, puerto, usuario, contraseña]
        destinatario (str): Email del destinatario.
        asunto (str): Asunto del correo.
        mensaje (str): Mensaje HTML del correo.
        archivo (str, opcional): Ruta a archivo a adjuntar. Default "".
        copia_oculta (bool, opcional): Enviar copia oculta al remitente. Default True.

    Returns:
        tuple:
            - bool: True si se envió correctamente, False si hubo error.
            - dict: Información de errores o mensaje de éxito.
    """
    Aux = False
    Errores = {}

    remitente, smtp_server, smtp_port, smtp_user, smtp_pass = credenciales

    context = ssl.create_default_context()
    Cadena = ""

    # Preparar mensaje
    header = MIMEMultipart()
    header['Subject'] = asunto
    header['From'] = remitente
    header['To'] = destinatario
    if copia_oculta:
        header['Bcc'] = remitente

    # Componer cuerpo HTML
    header.attach(MIMEText(mensaje, 'html'))

    # Adjuntar archivo si existe
    if archivo and os.path.isfile(archivo):
        adjunto = MIMEBase('application', 'octet-stream')
        adjunto.set_payload(open(archivo, "rb").read())
        encode_base64(adjunto)
        adjunto.add_header(
            'Content-Disposition',
            f'attachment; filename="{os.path.basename(archivo)}"'
        )
        header.attach(adjunto)

    # Intentar enviar correo
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as servidor:
            servidor.login(smtp_user, smtp_pass)
            servidor.sendmail(remitente, destinatario, header.as_string())
        Aux = True
        Cadena = f'Correo enviado a {destinatario} vía {smtp_server} con asunto "{asunto}"'
        logging.info(Cadena)
        Errores['Mensaje'] = Cadena

    except smtplib.SMTPAuthenticationError:
        Cadena = f'Contraseña incorrecta para {smtp_user} en {smtp_server}'
        logging.error(Cadena)
    except smtplib.SMTPSenderRefused:
        Cadena = f'Remitente {remitente} rechazado por {smtp_server}'
        logging.error(Cadena)
    except smtplib.SMTPRecipientsRefused:
        Cadena = f'Destinatario {destinatario} rechazado por {smtp_server}'
        logging.error(Cadena)
    except smtplib.SMTPDataError:
        Cadena = f'Error enviando mensaje para {smtp_user} vía {smtp_server}'
        logging.error(Cadena)
    except smtplib.SMTPException as e:
        Cadena = f'Excepción SMTP: {e}'
        logging.error(e)

    if Cadena and not Aux:
        Errores['Error'] = Cadena

    return Aux, Errores
