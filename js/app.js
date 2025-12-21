// Invasive Species Intelligence Tool v0.2
// Application Logic

/* =========================================================================
   1. INITIALIZATION & CONFIG
   ========================================================================= */

const CONFIG = {
    startView: [44.0, -87.2], // Centered on Lake Michigan Risk Zone
    zoomLevel: 7,
    colors: {
        riskHigh: '#ef4444',
        riskMed: '#f59e0b',
        riskLow: '#10b981',
        sighting: '#f97316',
        vessel: '#a855f7'
    }
};

const map = L.map('map', {
    zoomControl: false, // We'll move it or style it later if needed
    attributionControl: false
}).setView(CONFIG.startView, CONFIG.zoomLevel);

// Add custom attribution bottom right
L.control.attribution({ position: 'bottomright' }).addTo(map);

// Dark Mode Basemap (CartoDB Dark Matter)
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

/* =========================================================================
   2. LAYER DEFINITIONS (LAYER 1 - STABLE BASELINE)
   ========================================================================= */

const LAYERS = {};
const layerGroups = {
    sightings: L.layerGroup().addTo(map),
    habitat: L.layerGroup().addTo(map),
    traffic: L.layerGroup(),
    iuu: L.layerGroup(),
    risk_overlay: L.layerGroup().addTo(map) // AI Layer
};

// --- DATA: KNOWN SIGHTINGS (Layer 1) ---
const knownSightings = [
    { coords: [43.09, -89.38], label: "Bighead Carp", detail: "Yahara River, WI (Confirmed)", color: CONFIG.colors.sighting },
    { coords: [42.68, -89.02], label: "Silver Carp", detail: "Sugar River, WI (Confirmed)", color: CONFIG.colors.sighting },
    { coords: [41.51, -88.12], label: "Sea Lamprey", detail: "Des Plaines River, IL (Historical)", color: "#facc15" }
];

knownSightings.forEach(pt => {
    L.circleMarker(pt.coords, {
        radius: 6,
        color: '#fff',
        weight: 1,
        fillColor: pt.color,
        fillOpacity: 0.9
    })
        .bindPopup(`<div class="popup-header">${pt.label}</div><div class="popup-row">${pt.detail}</div>`)
        .addTo(layerGroups.sightings);
});

// --- DATA: HABITAT (Layer 1) ---
// Simplified polygon
L.polygon([
    [45.0, -87.2], [44.6, -86.8], [44.2, -87.0], [44.4, -87.5]
], {
    color: CONFIG.colors.riskMed,
    weight: 1,
    fillColor: CONFIG.colors.riskMed,
    fillOpacity: 0.15,
    dashArray: '5, 5'
}).bindTooltip("Known Suitable Habitat Zone").addTo(layerGroups.habitat);


// --- DATA: TRAFFIC / IUU (Context) ---
// We keep this for continuity but default it to off or separate
const vessels = [
    { coords: [44.0, -87.5], label: "Cargo Vessel A", type: "Commercial" },
    { coords: [43.8, -87.1], label: "Cargo Vessel B", type: "Commercial" }
];

vessels.forEach(v => {
    L.circleMarker(v.coords, {
        radius: 4,
        color: CONFIG.colors.vessel,
        fillColor: CONFIG.colors.vessel,
        fillOpacity: 0.8
    }).bindTooltip(v.label).addTo(layerGroups.traffic);
});


/* =========================================================================
   3. AI LAYER IMPLEMENTATION (LAYER 2)
   ========================================================================= */

async function loadAILayer() {
    try {
        console.log("Fetching AI Predictions from Hybrid Backend...");
        // POINT THIS TO YOUR LOCAL PYTHON API
        const response = await fetch('http://127.0.0.1:8000/predict');

        if (!response.ok) throw new Error("API Response Error");

        const data = await response.json();
        renderRiskPolygons(data.regions);

        // Load the first region's data into the side panel as default context
        if (data.regions.length > 0) {
            updateSidePanel(data.regions[0].properties);
        }

    } catch (error) {
        console.error("Failed to load AI Layer:", error);
        // Fallback or Alert? 
        // Per spec: "Map still loads, Known observations still display" -> We rely on Layer 1.
    }
}

function renderRiskPolygons(regions) {
    regions.forEach(region => {
        // STYLE FUNCTION
        const getStyle = (props) => {
            const score = props.risk_score;
            let color = CONFIG.colors.riskLow;
            if (score > 0.5) color = CONFIG.colors.riskMed;
            if (score > 0.8) color = CONFIG.colors.riskHigh;

            // Pulse animation class is handled via className if possible in Leaflet, 
            // but L.geoJSON style 'className' option supports SVG classes.
            return {
                color: color,
                weight: 2,
                opacity: 0.8,
                fillColor: color,
                fillOpacity: 0.35,
                className: score > 0.8 ? 'risk-polygon-high' : ''
            };
        };

        const geoLayer = L.geoJSON(region.geometry, {
            style: getStyle(region.properties),
            onEachFeature: (feature, layer) => {
                layer.on('click', () => {
                    updateSidePanel(region.properties);
                    // Highlight structure?
                    layer.openPopup();
                });

                // Simple hover tooltip
                layer.bindTooltip(`Risk Score: ${(region.properties.risk_score * 100).toFixed(0)}`, {
                    permanent: false,
                    direction: 'center',
                    className: 'glass-panel' // Reuse glass panel for tooltip style? might need tweaks
                });

                // Detailed Popup
                const popupContent = `
                    <div class="popup-header">AI Risk Analysis: ${region.properties.risk_label}</div>
                    <div class="popup-row">
                        <span>Score:</span>
                        <strong style="color:${getStyle(region.properties).color}">${region.properties.risk_score}</strong>
                    </div>
                    <div class="popup-row">
                        <span>Confidence:</span>
                        <span>${region.properties.confidence}</span>
                    </div>
                    <div style="margin-top:0.5rem; font-size:0.8rem; border-top:1px solid #333; padding-top:0.25rem;">
                        <em>${region.properties.explanation}</em>
                    </div>
                `;
                layer.bindPopup(popupContent);
            }
        });

        geoLayer.addTo(layerGroups.risk_overlay);
    });
}

function updateSidePanel(props) {
    // Update the "Live Analysis" card
    const container = document.getElementById('prediction-content');

    // Animate update (simple fade)
    container.style.opacity = '0.5';

    setTimeout(() => {
        document.getElementById('pred-species').innerText = props.species;

        const scoreEl = document.getElementById('pred-score');
        scoreEl.innerText = (props.risk_score * 100).toFixed(0) + "/100";

        // Color code the score
        if (props.risk_score > 0.8) scoreEl.style.color = CONFIG.colors.riskHigh;
        else if (props.risk_score > 0.5) scoreEl.style.color = CONFIG.colors.riskMed;
        else scoreEl.style.color = CONFIG.colors.riskLow;

        document.getElementById('pred-expl').innerHTML = `
            ${props.explanation} <br><br>
            <strong>Key Drivers:</strong>
            <ul style="padding-left:1rem; margin-bottom:0;">
                ${props.drivers.map(d => `<li>${d}</li>`).join('')}
            </ul>
        `;

        container.style.opacity = '1';
    }, 200);
}

// --- EXECUTE ---
loadAILayer();


/* =========================================================================
   4. INTERACTIVITY & TOGGLES
   ========================================================================= */

document.querySelectorAll('.layer-checkbox').forEach(box => {
    box.addEventListener('change', (e) => {
        const layerName = e.target.value;
        const layerInfo = layerGroups[layerName];

        if (layerInfo) {
            if (e.target.checked) {
                map.addLayer(layerInfo);
            } else {
                map.removeLayer(layerInfo);
            }
        }
    });
});

console.log("System Initialized: Invasive Species Intelligence v0.2");
