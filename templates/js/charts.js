// charts.js
// Funciones para actualizar el gráfico de temperaturas usando Chart.js

/**
 * Actualiza el gráfico de temperaturas con los datos proporcionados.
 * @param {Array} data - Lista de lecturas históricas, cada elemento con:
 *                       { fecha_hora: string, temperatura: number, ubicacion: string }
 */
function updateChart(data) {
  if (!data || data.length === 0) return; // No hacer nada si no hay datos

  // Obtener contexto del canvas
  const ctx = document.getElementById('tempChart').getContext('2d');

  // Si ya existe un gráfico previo, destruirlo antes de crear uno nuevo
  if (window.chart) {
    window.chart.destroy();
    window.chart = null;
  }

  // Agrupar los datos por ubicación
  const datasetsMap = {};
  data.forEach(d => {
    if (d.temperatura == null) return; // Ignorar lecturas sin temperatura
    const loc = d.ubicacion || 'Desconocida';
    if (!datasetsMap[loc]) datasetsMap[loc] = [];
    datasetsMap[loc].push({ x: d.fecha_hora, y: d.temperatura });
  });

  // Definir colores de las líneas (usar configuración si existe)
  const colors = config ? config.chartColors : [
    '#e74c3c','#3498db','#2ecc71','#f1c40f','#9b59b6','#1abc9c','#e67e22'
  ];

  // Convertir cada ubicación en un dataset de Chart.js
  const datasets = Object.keys(datasetsMap).map((loc, i) => ({
    label: loc,
    data: datasetsMap[loc],
    borderColor: colors[i % colors.length],
    backgroundColor: colors[i % colors.length] + '40', // 25% opacidad
    fill: false,
    tension: 0.3, // Curvatura de la línea
    pointRadius: 3 // Tamaño de los puntos
  }));

  // Crear gráfico de líneas
  window.chart = new Chart(ctx, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: currentFilter ? `Temperatura - ${currentFilter}` : 'Todas las ubicaciones'
        },
        legend: { position: 'top' }
      },
      scales: {
        x: { type: 'time', time: { unit: 'day' } }, // eje X temporal por día
        y: {
          suggestedMin: 15, // rango sugerido mínimo
          suggestedMax: 40, // rango sugerido máximo
          title: { display: true, text: '°C' }
        }
      }
    }
  });
}
