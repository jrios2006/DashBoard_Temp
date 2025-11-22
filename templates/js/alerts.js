// alerts.js
// Funciones para manejar alertas visuales en el frontend de Telemetría CPD

/**
 * Carga las alertas desde el backend y las muestra en el contenedor #alertas.
 * Se llama periódicamente para mantener la información actualizada.
 */
async function cargarAlertas() {
    try {
        // Petición al endpoint de alertas
        const r = await fetch("/api/alerts");
        const data = await r.json();

        const cont = document.getElementById("alertas");

        // Limpiar alertas previas
        cont.innerHTML = "";

        // Crear elementos div para cada alerta y añadir al contenedor
        data.alertas.forEach(a => {
            const div = document.createElement("div");
            div.className = `alerta alerta-${a.nivel}`; // Nivel: roja, amarilla, azul
            div.innerText = `${a.ubicacion}: ${a.texto}`;
            cont.appendChild(div);
        });

    } catch (e) {
        console.error("Error cargando alertas:", e);
    }
}

// Ejecutar cada 5 segundos para mantener la vista actualizada
setInterval(cargarAlertas, 5000);
cargarAlertas(); // Primera carga inmediata


/**
 * Verifica si existen alertas de spikes recientes y muestra un banner en la parte superior.
 * @returns {Promise<void>}
 */
async function checkSpikeAlerts() {
  try {
    // Endpoint filtrado por ubicación si existe currentFilter
    const url = currentFilter ? `/api/alerts?location=${encodeURIComponent(currentFilter)}` : `/api/alerts`;
    const res = await fetch(url);
    const { alertas } = await res.json();

    const banner = document.getElementById('alert-banner');
    const text = document.getElementById('alert-text');

    if (alertas && alertas.length > 0) {
      const a = alertas[0]; // Tomamos la alerta más crítica
      banner.style.display = 'block';
      banner.className = a.nivel; // Aplicar clase de nivel (roja, amarilla, azul)
      text.textContent = `ALERTA: ${a.texto}`;

      // Aplicar color definido en la configuración si existe
      if (config && config.colors[a.nivel]) {
        banner.style.backgroundColor = config.colors[a.nivel];
      }
    } else {
      // No hay alertas activas: ocultar banner
      banner.style.display = 'none';
    }
  } catch (e) {
    console.log("Alertas desactivadas o error:", e);
  }
}
