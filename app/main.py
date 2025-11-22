# app/main.py
"""
Microservicio de Telemetría CPD
--------------------------------
Este módulo define la aplicación FastAPI que expone:
- Dashboard web
- Endpoints para lecturas recientes, históricas y alertas
- WebSocket en tiempo real
- Loop periódico para envío de alertas por email
- Endpoint de estado de alertas

Se integra con el módulo 'module' que contiene:
- database.py → acceso a base de datos
- alertas.py → lógica de generación de alertas
- alertas_manager.py → gestión y envío periódico de alertas por email
"""

import json
import os
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import StringIO
import csv

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

# -------------------------------------------------------
# Importación de módulos propios
# -------------------------------------------------------
from .module.alertas_manager import alert_manager
from .module.alertas import generar_alertas
from .module.database import get_latest_readings, get_historical, get_unique_locations, detect_temperature_spikes

# -------------------------------------------------------
# Inicialización de la aplicación FastAPI
# -------------------------------------------------------
app = FastAPI(
    title="Telemetría CPD",
    description="Dashboard en tiempo real",
    version="1.0.0"
)

# -------------------------------------------------------
# Configuración de plantillas y archivos estáticos
# -------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "../templates")

# Montamos carpetas de CSS, JS y config para servir estáticos
app.mount("/css", StaticFiles(directory=os.path.join(TEMPLATES_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(TEMPLATES_DIR, "js")), name="js")
app.mount("/config", StaticFiles(directory=os.path.join(TEMPLATES_DIR, "config")), name="config")

# Plantillas Jinja2
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# -------------------------------------------------------
# Serializador JSON personalizado
# -------------------------------------------------------
def json_serializer(obj):
    """Convierte datetime, date y Decimal a tipos serializables en JSON."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

# -------------------------------------------------------
# ENDPOINTS PRINCIPALES
# -------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Página principal (Dashboard).
    Muestra las ubicaciones disponibles y se integra con la vista index.html.
    """
    locations = get_unique_locations()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "locations": locations
    })


@app.get("/api/latest")
async def api_latest(location: str | None = None):
    """
    Devuelve las últimas lecturas de temperatura y humedad.
    Se puede filtrar por ubicación.
    """
    return get_latest_readings(location)


@app.get("/api/historical")
async def api_historical(location: str | None = None, days: int = 1, format: str = "json"):
    """
    Devuelve lecturas históricas de los últimos 'days' días.
    Soporta formato JSON (default) o CSV para descarga.
    """
    data = get_historical(location, days)

    if format.lower() == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["fecha_hora", "ubicacion", "temperatura", "humedad"])
        for row in data:
            writer.writerow([
                row["fecha_hora"],
                row["ubicacion"],
                row.get("temperatura", ""),
                row.get("humedad", "")
            ])
        return Response(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=telemetria.csv"}
        )

    return data


@app.websocket("/ws/{location_filter}")
async def websocket_endpoint(websocket: WebSocket, location_filter: str):
    """
    WebSocket para enviar en tiempo real las últimas lecturas filtradas por ubicación.
    Cada 5 segundos envía los datos actuales.
    """
    await websocket.accept()
    print(f"[WS] Cliente conectado → filtro: '{location_filter}'")

    filter_val = None if location_filter in ("null", "undefined", "", None) else location_filter

    try:
        while True:
            if websocket.client_state.name != "CONNECTED":
                print("[WS] Cliente desconectado (detected by state)")
                break

            data = get_latest_readings(filter_val)
            json_str = json.dumps(data, default=json_serializer, ensure_ascii=False)

            try:
                await websocket.send_text(json_str)
                print(f"[WS] Enviados {len(data)} registros correctamente")
            except RuntimeError as e:
                print(f"[WS] Conexión cerrada al enviar: {e}")
                break

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        print("[WS] Cliente desconectado (exception)")
    except Exception as e:
        print(f"[WS] Error inesperado: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
        print("[WS] Conexión finalizada")


@app.get("/api/alerts")
async def api_alerts(location: str | None = None):
    """
    Devuelve alertas detectadas por subidas/bajadas bruscas (spikes) de temperatura.
    """
    alertas = await detect_temperature_spikes(location)
    return {"alertas": alertas, "total": len(alertas)}


@app.get("/api/locations")
async def api_locations():
    """
    Lista todas las ubicaciones disponibles.
    """
    return {"locations": get_unique_locations()}

# -------------------------------------------------------
# LOOP PERIÓDICO DE ENVÍO DE ALERTAS POR EMAIL
# -------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Al iniciar el servidor, lanza un loop en background
    que revisa periódicamente si toca enviar alertas por email.
    """
    asyncio.create_task(loop_envio_alertas())

async def loop_envio_alertas():
    """
    Loop infinito que revisa cada minuto si toca enviar alertas.
    Se apoya en la instancia global alert_manager.
    """
    while True:
        try:
            await alert_manager.enviar_alertas_si_toca()
        except Exception as e:
            print("[MAIL] Error:", e)
        await asyncio.sleep(60)


# -------------------------------------------------------
# ENDPOINT PARA CONSULTAR ESTADO DE ALERTAS
# -------------------------------------------------------
@app.get("/api/alertas-estado")
async def alertas_estado():
    """
    Devuelve información sobre el estado de alertas por email:
    - Último envío
    - Alertas enviadas
    - Próximo envío aproximado según intervalo configurado
    """
    proximo = alert_manager.proximo_envio()
    return {
        "ultima_envio": alert_manager.last_alert_sent.strftime("%Y-%m-%d %H:%M:%S") if alert_manager.last_alert_sent else None,
        "alertas_enviadas": alert_manager.ultimas_alertas,
        "proximo_envio_aproximado": proximo.strftime("%Y-%m-%d %H:%M:%S") if proximo else None
    }
