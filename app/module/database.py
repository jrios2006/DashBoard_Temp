"""
database.py

Módulo de acceso a la base de datos MariaDB para el microservicio de telemetría.

Funciones principales:
- load_credentials(): carga credenciales de la base de datos desde config/credenciales.json
- get_connection(): obtiene una conexión a MariaDB
- get_unique_locations(): devuelve la lista de ubicaciones únicas
- get_latest_readings(location_filter): obtiene la última lectura por ubicación
- get_historical(location_filter, days): obtiene lecturas históricas de los últimos 'days' días
- detect_temperature_spikes(location): detecta subidas/bajadas bruscas de temperatura recientes

Dependencias:
- mariadb
- json
- os
- datetime
- typing
"""

import mariadb
import json
import os
from typing import List, Optional
from datetime import timedelta, datetime

# -------------------------------
# Rutas absolutas al directorio app/config
# -------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENCIALES_PATH = os.path.join(BASE_DIR, "config", "credenciales.json")


def load_credentials() -> dict:
    """
    Carga las credenciales de acceso a la base de datos desde app/config/credenciales.json.

    Returns:
        dict: Diccionario con los datos de conexión a MariaDB.
    """
    with open(CREDENCIALES_PATH, 'r') as f:
        return json.load(f)["database"]


def get_connection():
    """
    Obtiene una conexión activa a la base de datos MariaDB usando las credenciales cargadas.

    Returns:
        mariadb.connection: Objeto de conexión a MariaDB.
    """
    creds = load_credentials()
    return mariadb.connect(**creds)


def get_unique_locations() -> List[str]:
    """
    Obtiene todas las ubicaciones distintas presentes en la tabla telemetria_sensores.

    Returns:
        List[str]: Lista de nombres de ubicaciones ordenadas alfabéticamente.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT ubicacion FROM telemetria_sensores WHERE ubicacion IS NOT NULL ORDER BY ubicacion"
    )
    locations = [row[0] for row in cur.fetchall()]
    conn.close()
    return locations


def get_latest_readings(location_filter: Optional[str] = None) -> List[dict]:
    """
    Obtiene la última lectura registrada por cada ubicación.

    Args:
        location_filter (Optional[str]): Nombre de la ubicación a filtrar. Si es None, devuelve todas.

    Returns:
        List[dict]: Lista de diccionarios con los datos de la última lectura por ubicación.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    sql = """
        SELECT t.*
        FROM telemetria_sensores t
        INNER JOIN (
            SELECT ubicacion, MAX(fecha_hora) AS max_fecha
            FROM telemetria_sensores
            WHERE (ubicacion = %s OR %s IS NULL)
            GROUP BY ubicacion
        ) latest ON t.ubicacion = latest.ubicacion AND t.fecha_hora = latest.max_fecha
        ORDER BY t.temperatura DESC, t.ubicacion
    """
    cur.execute(sql, (location_filter, location_filter))
    data = cur.fetchall()
    conn.close()
    return data


def get_historical(location_filter: Optional[str] = None, days: int = 1) -> List[dict]:
    """
    Obtiene lecturas históricas de los últimos 'days' días para una ubicación específica o todas.

    Args:
        location_filter (Optional[str]): Ubicación a filtrar. None devuelve todas.
        days (int): Número de días hacia atrás a recuperar (por defecto 1).

    Returns:
        List[dict]: Lista de lecturas históricas con fecha_hora, temperatura, humedad y ubicación.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    sql = """
        SELECT fecha_hora, temperatura, humedad, ubicacion
        FROM telemetria_sensores
        WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL %s DAY)
    """
    params = [days]

    if location_filter:
        sql += " AND ubicacion = %s"
        params.append(location_filter)

    sql += " ORDER BY fecha_hora ASC"
    cur.execute(sql, params)
    data = cur.fetchall()
    conn.close()
    return data


async def detect_temperature_spikes(location: Optional[str] = None) -> List[dict]:
    """
    Detecta subidas o bajadas bruscas de temperatura en los últimos 15-20 minutos.

    Args:
        location (Optional[str]): Ubicación a filtrar. Si es None, analiza todas.

    Returns:
        List[dict]: Lista de alertas con los siguientes campos:
            - ubicacion: str
            - nivel: 'roja', 'amarilla', 'azul'
            - texto: descripción de la alerta
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    sql = """
        SELECT ubicacion, temperatura, fecha_hora
        FROM telemetria_sensores
        WHERE fecha_hora >= DATE_SUB(NOW(), INTERVAL 20 MINUTE)
          AND temperatura IS NOT NULL
    """
    params = []
    if location:
        sql += " AND ubicacion = %s"
        params.append(location)

    sql += " ORDER BY ubicacion, fecha_hora DESC"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    # Agrupar lecturas por ubicación
    datos = {}
    for r in rows:
        loc = r["ubicacion"]
        datos.setdefault(loc, []).append(r)

    alertas = []

    for ubicacion, lecturas in datos.items():
        if len(lecturas) < 2:
            continue

        lecturas.sort(key=lambda x: x["fecha_hora"])
        ultima = lecturas[-1]

        for i in range(len(lecturas) - 2, -1, -1):
            anterior = lecturas[i]
            if anterior["temperatura"] is not None:
                break
        else:
            continue

        delta_temp = ultima["temperatura"] - anterior["temperatura"]
        delta_min = (ultima["fecha_hora"] - anterior["fecha_hora"]).total_seconds() / 60

        if delta_min <= 0 or delta_min > 20:
            continue

        texto = f"{ubicacion}: {delta_temp:+.1f}°C en {delta_min:.0f} min"

        if delta_temp >= 4.0 and delta_min <= 10:
            alertas.append({"ubicacion": ubicacion, "nivel": "roja", "texto": f"SUBIDA CRÍTICA → {texto} ¡POSIBLE EMERGENCIA!"})
        elif delta_temp >= 2.5 and delta_min <= 10:
            alertas.append({"ubicacion": ubicacion, "nivel": "amarilla", "texto": f"Subida rápida → {texto}"})
        elif delta_temp <= -5.0 and delta_min <= 15:
            alertas.append({"ubicacion": ubicacion, "nivel": "azul", "texto": f"Bajada brusca → {texto} → Revisar sensor"})

    prioridad = {"roja": 0, "amarilla": 1, "azul": 2}
    alertas.sort(key=lambda x: prioridad.get(x["nivel"], 9))

    return alertas
