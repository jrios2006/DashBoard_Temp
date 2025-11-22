# Microservicio de Telemetría CPD

Sistema de monitorización en tiempo real de temperatura y humedad de un CPD (Centro de Procesamiento de Datos).  
Permite detectar alertas por umbrales y spikes de temperatura, mostrar información en la UI web y enviar notificaciones por correo electrónico.

---

## 📁 Estructura del Proyecto

```bash
── app
│ ├── config
│ │ ├── credenciales.json # Credenciales de DB y SMTP
│ │ └── parametros.json # Configuración del backend (umbrales, email, alertas)
│ ├── main.py # Entrada principal FastAPI / WebSocket
│ ├── module
│ │ ├── alertas_manager.py # Gestor de alertas y envío de emails
│ │ ├── alertas.py # Lógica de generación de alertas
│ │ ├── correo.py # Funciones para enviar correos por SMTP SSL
│ │ ├── database.py # Acceso a la base de datos MariaDB
│ │ └── init.py
├── templates
│ ├── config
│ │ └── settings.json # Configuración frontend (umbrales, colores, gráficos)
│ ├── css
│ │ └── style.css # Estilos de la UI
│ ├── index.html # Página web principal
│ └── js
│ ├── alerts.js # Actualización de alertas en la UI
│ ├── charts.js # Actualización de gráficos
│ └── main.js # Lógica principal del frontend
├── requirements.txt # Dependencias Python
└── readme.me # Información general
```


---

## ⚙️ Instalación

1. Crear entorno virtual (opcional pero recomendado):

```bash
python -m venv kivy-env
source kivy-env/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Configurar credenciales:

* `app/config/credenciales.json`:

```json
{
  "database": {
    "host": "localhost",
    "user": "usuario",
    "password": "contraseña",
    "database": "telemetria"
  },
  "smtp": [
    "remitente@dominio.com",
    "smtp.dominio.com",
    465,
    "usuario",
    "contraseña"
  ]
}

```

* `app/config/parametros.json`:

```json
{
  "thresholds": {
    "warning": 15,
    "danger": 18
  },
  "email": {
    "enabled": true,
    "destinatarios": ["operador@dominio.com"],
    "intervalo_envio_min": 60,
    "enviar_alertas": true
  },
  "alertas": {
    "detectar_spikes": true,
    "spike_critica": 4.0,
    "spike_media": 2.5,
    "tiempo_spike_minutos": 10
  }
}
```

* `templates/config/settings.json` (rfontend):

```json
{
  "thresholds": {
    "danger": 15,
    "warning": 18
  },
  "colors": {
    "danger": "#e74c3c",
    "warning": "#e67e22",
    "info": "#3498db"
  },
  "chartColors": ["#e74c3c","#3498db","#2ecc71","#f1c40f","#9b59b6","#1abc9c","#e67e22"]
}
```

---

## 🚀 Uso

Ejecutar el microservicio con Uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* Acceder a la UI en: http://localhost:8000
* WebSocket: /ws/{ubicacion} para recibir lecturas en tiempo real.

---

## 🚀 Componentes

### Backend

* `main.py`: arranca FastAPI, maneja WebSocket y APIs REST.
* `module/alertas.py`: genera alertas por umbral y por spikes de temperatura.
* `module/alertas_manager.py`: gestiona envío de alertas por email y controla intervalos.
* `module/correo.py`: envía correos mediante SMTP SSL.
* `module/database.py`: consulta MariaDB para lecturas actuales e históricas.

### frontend

* `index.html`: interfaz web principal.
* `css/style.css:` estilos para tarjetas, banners y gráficos.
* `js/main.js`: lógica principal (carga de datos, WebSocket, actualización de UI).
* `js/charts.js`: genera y actualiza los gráficos con Chart.js.
* `js/alerts.js`: refresco de alertas y banner de spikes.

---

## 📊 Flujo de datos

1. Lecturas de sensores se almacenan en MariaDB.
2. Backend (`alertas.py` y `alertas_manager.py`) genera alertas:
    * Umbrales: comparando con `parametros.json`.
    * Spikes: detectando subidas/bajadas rápidas de temperatura.
3. Frontend (main.js) recibe:
    * Lecturas actuales vía WebSocket.
    * Datos históricos vía REST API (`/api/historical`).
    * Alertas vía /api/alerts.
4. Banner de alertas y tarjetas se colorean según `templates/config/settings.json`.

---

## 📌 Notas importantes

* Diferencia entre JSONs:
    * `parametros.json` → backend, lógica de alertas y email.
    * `settings.json` → frontend, colores y umbrales visuales.
* Credenciales deben estar correctamente configuradas para DB y SMTP.
* El envío de emails respeta el intervalo configurado (intervalo_envio_min).

---

## 📚 Dependencias

* Python 3.10+
* FastAPI
* Uvicorn
* MariaDB connector (mariadb)
* Chart.js (frontend, vía CDN)

---

## Para hacer

1. Ver dónde se requiere y si este másuina tiene acceso al servidor de base de datos.
2. Configurar apache o nginx como proxy inverso
3. Dotar de una seguridad mínima para que no sea público
4. Añadir más ubicaciones y sensores para complementar el dashboard básico

---

