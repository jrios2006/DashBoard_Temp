"""
alertas_manager.py

Gestor de alertas y envío de correos electrónicos para el microservicio de telemetría.

Clases:
- AlertManager: controla el envío periódico de alertas por email, registro de últimas alertas,
  y cálculo del próximo envío.

Dependencias:
- module.alertas (generar_alertas)
- module.correo (EnviarCorreoSSL)
- datetime, json, os
"""

from datetime import datetime, timedelta
from .alertas import generar_alertas
from .correo import EnviarCorreoSSL
import json
import os

# ---------------------------------------------------------------
# Ruta al fichero de configuración del backend
# ---------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "parametros.json")
CREDENCIALES_PATH = os.path.join(ROOT_DIR, "config", "credenciales.json")

if not os.path.isfile(CONFIG_PATH):
    raise FileNotFoundError(f"No se encuentra el fichero de configuración: {CONFIG_PATH}")

if not os.path.isfile(CREDENCIALES_PATH):
    raise FileNotFoundError(f"No se encuentra el fichero de credenciales SMTP: {CREDENCIALES_PATH}")


class AlertManager:
    """
    Gestor de alertas de temperatura.

    Atributos:
        last_alert_sent (datetime | None): Fecha/hora del último envío de alertas.
        ultimas_alertas (list): Lista de alertas enviadas en el último envío.
    """

    def __init__(self):
        self.last_alert_sent: datetime | None = None
        self.ultimas_alertas: list = []

    def load_config(self) -> dict:
        """
        Carga la configuración del backend desde config/parametros.json.

        Returns:
            dict: Configuración del sistema, incluyendo thresholds y parámetros de email.
        """
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)

    def load_smtp_credentials(self) -> list:
        """
        Carga las credenciales SMTP desde config/credenciales.json.

        Returns:
            list: [remitente, servidor_smtp, puerto, usuario, contraseña]
        """
        with open(CREDENCIALES_PATH, "r") as f:
            return json.load(f)["smtp"]

    async def enviar_alertas_si_toca(self):
        """
        Revisa si corresponde enviar alertas por email según la configuración de intervalos.
        Si toca, genera alertas, prepara el HTML y envía el correo a los destinatarios configurados.
        """
        config = self.load_config()
        email_cfg = config.get("email", {})

        if not email_cfg.get("enabled", False):
            return

        ahora = datetime.now()
        intervalo = timedelta(minutes=email_cfg.get("intervalo_envio_min", 60))

        if self.last_alert_sent and ahora - self.last_alert_sent < intervalo:
            return

        # Generar alertas
        alertas = await generar_alertas()
        if not alertas:
            return

        # Guardar estado
        self.ultimas_alertas = alertas.copy()
        self.last_alert_sent = ahora

        # Preparar HTML del correo
        html = "<h3>Alertas de Temperatura</h3><ul>"
        for a in alertas:
            html += f"<li><strong>{a['ubicacion']}</strong>: {a['texto']}</li>"
        html += "</ul>"

        asunto = "⚠️ ALERTA DE TEMPERATURA EN CPD"
        smtp_cred = self.load_smtp_credentials()

        # Enviar a todos los destinatarios
        for dest in email_cfg.get("destinatarios", []):
            EnviarCorreoSSL(
                smtp_cred,
                destinatario=dest,
                asunto=asunto,
                mensaje=html,
                archivo="",
                copia_oculta=False
            )

        print(f"[MAIL] Enviadas {len(alertas)} alertas a {', '.join(email_cfg.get('destinatarios', []))} a las {ahora.strftime('%Y-%m-%d %H:%M:%S')}")

    def proximo_envio(self) -> datetime | None:
        """
        Calcula la fecha/hora aproximada del próximo envío de alertas según el intervalo configurado.

        Returns:
            datetime | None: Fecha/hora del próximo envío, o None si nunca se ha enviado.
        """
        config = self.load_config()
        intervalo_min = config.get("email", {}).get("intervalo_envio_min", 60)

        if self.last_alert_sent:
            return self.last_alert_sent + timedelta(minutes=intervalo_min)
        return None


# Instancia global del manager (singleton)
alert_manager = AlertManager()
