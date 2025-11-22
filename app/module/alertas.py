"""
alertas.py

Lógica de generación de alertas para el microservicio de telemetría.

Funciones principales:
- load_backend_config(): carga parámetros desde config/parametros.json
- generar_alertas(location=None): genera alertas visuales y de spikes para la web

Dependencias:
- module.database (get_latest_readings, detect_temperature_spikes)
- datetime, json, os
"""

from datetime import datetime
from .database import get_latest_readings, detect_temperature_spikes
import json
import os

# ---------------------------------------------------------------
# Ruta al fichero de configuración del backend
# ---------------------------------------------------------------
# Usamos la carpeta raíz del proyecto para localizar config/parametros.json
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config", "parametros.json")

if not os.path.isfile(CONFIG_PATH):
    raise FileNotFoundError(f"No se encuentra el fichero de configuración: {CONFIG_PATH}")


# ---------------------------------------------------------------
# Funciones
# ---------------------------------------------------------------

def load_backend_config() -> dict:
    """
    Carga la configuración del microservicio desde config/parametros.json.

    Returns:
        dict: Diccionario con thresholds, configuración de alertas y otros parámetros.
    """
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


async def generar_alertas(location: str | None = None) -> list[dict]:
    """
    Genera alertas combinando:
    1) Alertas por umbral (warning/danger) según la temperatura actual.
    2) Alertas por spikes de temperatura detectados en los últimos 15-20 minutos.

    Args:
        location (Optional[str]): Ubicación a filtrar. Si es None, se generan alertas para todas.

    Returns:
        List[dict]: Lista de alertas ordenadas por prioridad ('roja', 'amarilla', 'azul').
            Cada alerta contiene:
            - ubicacion: str
            - nivel: str ('roja', 'amarilla', 'azul')
            - texto: str, descripción de la alerta
    """
    config = load_backend_config()
    thresholds = config["thresholds"]

    alertas = []

    # ---------------------------------------------------------------
    # 1) Alertas instantáneas por valores actuales
    # ---------------------------------------------------------------
    lecturas = get_latest_readings(location)
    for r in lecturas:
        temp = r["temperatura"]
        ubic = r["ubicacion"]

        if temp >= thresholds["danger"]:
            alertas.append({
                "ubicacion": ubic,
                "nivel": "roja",
                "texto": f"TEMPERATURA CRÍTICA {temp}°C en {ubic}"
            })
        elif temp >= thresholds["warning"]:
            alertas.append({
                "ubicacion": ubic,
                "nivel": "amarilla",
                "texto": f"Temperatura elevada {temp}°C en {ubic}"
            })

    # ---------------------------------------------------------------
    # 2) Alertas por spikes
    # ---------------------------------------------------------------
    if config.get("alertas", {}).get("detectar_spikes", False):
        spikes = await detect_temperature_spikes(location)
        alertas.extend(spikes)

    # ---------------------------------------------------------------
    # Ordenar alertas por prioridad: roja > amarilla > azul
    # ---------------------------------------------------------------
    prioridad = {"roja": 0, "amarilla": 1, "azul": 2}
    alertas.sort(key=lambda x: prioridad.get(x["nivel"], 99))

    return alertas
