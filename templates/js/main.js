// main.js
// Control principal del dashboard de telemetría CPD en tiempo real

// Variables globales
let ws = null;           // WebSocket para recibir datos en tiempo real
let currentFilter = '';  // Ubicación actualmente seleccionada
let chart = null;        // Objeto Chart.js
let config = null;       // Configuración de thresholds y colores

// Al cargar la página
document.addEventListener('DOMContentLoaded', async () => {
  await loadConfig();        // Cargar umbrales y colores desde config/settings.json
  await populateLocations(); // Rellenar select de ubicaciones reales desde /api/locations
  connectWebSocket();        // Conectar WebSocket para lecturas en tiempo real
  loadData();                // Cargar datos históricos iniciales
  checkSpikeAlerts();        // Revisar alertas por spikes
  setInterval(checkSpikeAlerts, 30000); // Revisar spikes cada 30s
});


// ------------------------------
// FUNCIONES PRINCIPALES
// ------------------------------

// Cargar archivo de configuración
async function loadConfig() {
  const res = await fetch('config/settings.json');
  config = await res.json(); // Guardar thresholds y colores globalmente
}

// Llenar select de ubicaciones
async function populateLocations() {
  const select = document.getElementById('locationFilter');

  const res = await fetch("/api/locations");
  const data = await res.json();

  // Vaciar select antes de rellenar
  select.innerHTML = '<option value="">Todas las ubicaciones</option>';

  // Crear option por cada ubicación
  data.locations.forEach(loc => {
    const option = document.createElement('option');
    option.value = loc;
    option.textContent = loc;
    select.appendChild(option);
  });
}

// Conectar WebSocket para recibir lecturas en tiempo real
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
  if (ws) ws.close();

  const filterParam = currentFilter ? encodeURIComponent(currentFilter) : 'null';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/${filterParam}`);

  ws.onopen = () => console.log("WebSocket conectado");
  ws.onmessage = (e) => updateCurrent(JSON.parse(e.data));
  ws.onclose = () => setTimeout(connectWebSocket, 3000); // reconexión automática
}

// Cargar datos históricos y actualizar gráfico
function loadData() {
  const loc = document.getElementById('locationFilter').value || '';
  const days = document.getElementById('daysFilter').value;

  if (loc !== currentFilter) {
    currentFilter = loc;
    connectWebSocket();
  }

  document.getElementById('loading').style.display = 'inline';

  let url = `/api/historical?days=${days}`;
  if (currentFilter) url += `&location=${encodeURIComponent(currentFilter)}`;

  fetch(url)
    .then(r => r.json())
    .then(data => {
      updateChart(data);
      document.getElementById('loading').style.display = 'none';
    })
    .catch(() => document.getElementById('loading').style.display = 'none');
}

// Actualizar la sección de lecturas actuales en la página
function updateCurrent(data) {
  const container = document.getElementById('current-readings');
  container.innerHTML = `<h2 style="margin-bottom:15px;color:#2c3e50;">
    Temperatura Actual ${currentFilter ? `- ${currentFilter}` : '(todas)'}
  </h2>`;

  if (!data || data.length === 0) {
    container.innerHTML += '<p><em>Sin datos</em></p>';
    return;
  }

  // Ordenar por temperatura descendente
  data.sort((a,b) => (b.temperatura||0)-(a.temperatura||0));

  data.forEach(d => {
    const temp = d.temperatura != null ? d.temperatura.toFixed(1)+'°C' : 'N/A';
    const hum = d.humedad != null ? d.humedad.toFixed(1)+'%' : 'N/A';
    const time = new Date(d.fecha_hora).toLocaleString('es-ES');

    const isDanger = config && d.temperatura > config.thresholds.danger;
    const isWarning = config && d.temperatura > config.thresholds.warning && d.temperatura <= config.thresholds.danger;

    container.innerHTML += `
      <div class="card ${isDanger ? 'danger' : isWarning ? 'warning' : ''}">
        <strong>${d.ubicacion}</strong><br>
        <span class="temp">${temp}</span> | ${hum}<br>
        <small>${time}</small>
        ${isDanger ? '<div class="alert-badge">¡ALERTA TÉRMICA!</div>' : ''}
      </div>`;
  });
}

// Exportar datos históricos a CSV
function exportToCSV() {
  const loc = document.getElementById('locationFilter').value || '';
  const days = document.getElementById('daysFilter').value;
  let url = `/api/historical?days=${days}&format=csv`;
  if (loc) url += `&location=${encodeURIComponent(loc)}`;

  fetch(url)
    .then(r => r.text())
    .then(csv => {
      const blob = new Blob([csv], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `telemetria_${loc||'todas'}_${days}d_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
    });
}
