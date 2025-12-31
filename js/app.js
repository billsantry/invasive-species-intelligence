// Invasive Species Intelligence Tool v0.4
// Application Logic

/* =========================================================================
   1. INITIALIZATION & CONFIG
   ========================================================================= */

const CONFIG = {
    startView: [44.2, -83.5], // Broad Great Lakes / Cross-Border perspective
    zoomLevel: 6,
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
    barriers: L.layerGroup().addTo(map),
    treatments: L.layerGroup(),
    trapping: L.layerGroup(),
    risk_overlay: L.layerGroup().addTo(map)
};

// --- DATA: KNOWN SIGHTINGS (Layer 1) ---
const knownSightings = [
    { coords: [43.09, -89.38], label: "Bighead Carp", detail: "Yahara River, WI (Confirmed)", color: CONFIG.colors.sighting, citation: "USGS BISON Database" },
    { coords: [42.68, -89.02], label: "Silver Carp", detail: "Sugar River, WI (Confirmed)", color: CONFIG.colors.sighting, citation: "USGS BISON Database" },
    { coords: [41.51, -88.12], label: "Sea Lamprey", detail: "Des Plaines River, IL (Historical)", color: "#facc15", citation: "Great Lakes FC Historical Data" },
    { coords: [42.32, -82.92], label: "Grass Carp", detail: "Windsor, ON (Live DFO Alert)", color: CONFIG.colors.sighting, citation: "Fisheries and Oceans Canada (DFO)" },
    { coords: [42.97, -82.40], label: "Round Goby", detail: "Sarnia, ON (Active Survey)", color: CONFIG.colors.sighting, citation: "Invasive Species Centre (Canada)" }
];

knownSightings.forEach(pt => {
    L.circleMarker(pt.coords, {
        radius: 6,
        color: '#fff',
        weight: 1,
        fillColor: pt.color,
        fillOpacity: 0.9
    })
        .bindPopup(`<div class="popup-header">${pt.label}</div><div class="popup-row">${pt.detail}</div><div style="font-size:0.7rem; color:#94a3b8; margin-top:0.5rem; border-top:1px solid rgba(255,255,255,0.1); padding-top:0.25rem;">Source: ${pt.citation}</div>`)
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
}).bindTooltip("Known Suitable Habitat Zone").addTo(layerGroups.habitat)
    .bindPopup(`<div class="popup-header">Habitat Suitability</div><div class="popup-row">Modeled as "High" for Asian Carp Complex</div><div style="font-size:0.7rem; color:#94a3b8; margin-top:0.5rem; border-top:1px solid rgba(255,255,255,0.1); padding-top:0.25rem;">Source: Scikit-Learn (Habitat Baseline v1)</div>`);


// --- DATA: GLFC INFRASTRUCTURE (BARRIERS, TREATMENTS, TRAPPING) ---
async function loadInfrastructure() {
    try {
        const apiUrl = (window.location.port === '8080' || window.location.protocol === 'file:')
            ? 'http://127.0.0.1:8000/infrastructure'
            : '/infrastructure';

        console.log(`Fetching GLFC Infrastructure from: ${apiUrl}`);
        const response = await fetch(apiUrl);
        if (!response.ok) throw new Error("Infrastructure API Error");

        const data = await response.json();

        data.points.forEach(pt => {
            let color = '#38bdf8'; // Default Barrier Blue
            let radius = 5;
            let group = layerGroups.barriers;
            let icon = '🛡️';

            if (pt.type === 'treatment') {
                color = '#ec4899'; // Pink for treatments
                group = layerGroups.treatments;
                icon = '🧪';
                radius = 4;
            } else if (pt.type === 'trapping') {
                color = '#facc15'; // Yellow for trapping
                group = layerGroups.trapping;
                icon = '🪤';
                radius = 6;
            } else if (pt.type === 'barrier' && pt.fc === 'No') {
                color = '#f87171'; // Red for non-control barriers
                icon = '⚠️';
            }

            L.circleMarker([pt.lat, pt.lon], {
                radius: radius,
                color: color,
                weight: 1.5,
                fillColor: '#0f172a',
                fillOpacity: 0.8,
            })
                .bindPopup(`
                <div class="popup-header" style="color:${color};">${icon} GLFC ${pt.type.charAt(0).toUpperCase() + pt.type.slice(1)}</div>
                <div class="popup-row" style="font-weight:600;">${pt.name}</div>
                ${pt.waterbody ? `<div class="popup-row"><span>Waterbody:</span> <span>${pt.waterbody}</span></div>` : ''}
                ${pt.fc ? `<div class="popup-row"><span>Control Status:</span> <span style="color:${pt.fc === 'Yes' ? '#4ade80' : '#f87171'}">${pt.fc === 'Yes' ? 'Foundational Control' : 'Alternative Structure'}</span></div>` : ''}
                <div style="font-size:0.65rem; color:#64748b; margin-top:0.4rem; border-top:1px solid rgba(255,255,255,0.1); padding-top:0.25rem;">
                    Source: GLFC Sea Lamprey Control Map
                </div>
            `)
                .addTo(group);
        });

    } catch (e) {
        console.error("Infrastructure loading failed:", e);
    }
}

loadInfrastructure();


// --- DATA: LIVE MARITIME INTELLIGENCE (Layer 1 - Procedural AIS) ---
class VesselEngine {
    constructor() {
        this.vessels = [
            { id: 'v-01', start: [44.0, -87.5], end: [41.8, -87.6], label: "Algoma Central", speed: 0.005, type: "Bulker" },
            { id: 'v-02', start: [42.3, -83.1], end: [41.5, -81.7], label: "Stewart J. Cort", speed: 0.008, type: "Laker" },
            { id: 'v-03', start: [44.8, -86.2], end: [43.6, -87.8], label: "Paul R. Tregurtha", speed: 0.006, type: "Iron Ore Carrier" },
            { id: 'v-04', start: [42.9, -82.4], end: [45.1, -83.4], label: "American Spirit", speed: 0.012, type: "General Cargo" }
        ];
        this.markers = {};
        this.init();
    }

    init() {
        this.vessels.forEach(v => {
            v.current = [...v.start];
            const marker = L.circleMarker(v.current, {
                radius: 4,
                color: CONFIG.colors.vessel,
                fillColor: CONFIG.colors.vessel,
                fillOpacity: 0.8,
                weight: 1
            });

            const searchUrl = `https://www.marinetraffic.com/en/ais/index/search/all/keyword:${v.label.replace(/ /g, '%20')}`;
            const popupContent = `
                <div class="popup-header">Live AIS: ${v.label}</div>
                <div class="popup-row"><span>Type:</span> <span>${v.type}</span></div>
                <div class="popup-row"><span>Status:</span> <span style="color:#4ade80">Underway</span></div>
                <div style="font-size:0.75rem; margin-top:0.5rem; border-top:1px solid rgba(255,255,255,0.1); padding-top:0.25rem;">
                    <a href="${searchUrl}" target="_blank" rel="noopener" style="color:var(--primary-action); text-decoration:none; display:flex; align-items:center; gap:0.3rem;">
                        <span>Source: AIS-Sim (Live Forecast)</span>
                        <span style="font-size:0.6rem;">↗</span>
                    </a>
                </div>
            `;

            marker.bindPopup(popupContent).addTo(layerGroups.traffic);
            this.markers[v.id] = marker;
        });

        // Start animation loop
        setInterval(() => this.updatePositions(), 1000);
    }

    updatePositions() {
        this.vessels.forEach(v => {
            // Simple interpolation towards end
            const dLat = v.end[0] - v.start[0];
            const dLon = v.end[1] - v.start[1];
            const dist = Math.sqrt(dLat * dLat + dLon * dLon);

            const stepLat = (dLat / dist) * v.speed * 0.1;
            const stepLon = (dLon / dist) * v.speed * 0.1;

            v.current[0] += stepLat;
            v.current[1] += stepLon;

            // Reset if reached destination
            if (Math.abs(v.current[0] - v.end[0]) < 0.01) {
                v.current = [...v.start];
            }

            this.markers[v.id].setLatLng(v.current);
        });
    }
}

const maritimeIntelligence = new VesselEngine();


/* =========================================================================
   3. AI LAYER IMPLEMENTATION (LAYER 2)
   ========================================================================= */

async function loadAILayer() {
    try {
        console.log("Fetching AI Predictions from Hybrid Backend...");
        // DYNAMIC API ROUTING
        // If on local static server (8080), point to local backend (8000). 
        // Otherwise (Production/Backend-served), use relative path.
        const apiUrl = (window.location.port === '8080' || window.location.protocol === 'file:')
            ? 'http://127.0.0.1:8000/predict'
            : '/predict';

        console.log(`Fetching AI Predictions from: ${apiUrl}`);
        const response = await fetch(apiUrl);

        if (!response.ok) throw new Error("API Response Error");

        const data = await response.json();
        renderRiskPolygons(data.regions);

        // Update Intelligence Feed
        if (data.alerts) {
            updateAlertsFeed(data.alerts);
        }

        // Load the first region's data into the side panel as default context
        if (data.regions.length > 0) {
            updateSidePanel(data.regions[0].properties);
        }

        // Update health status based on backend metadata
        if (data.metadata && data.metadata.health) {
            updateStatusUI(data.metadata.health);
        }

    } catch (error) {
        console.error("Failed to load AI Layer:", error);

        // Update Status to Red
        updateStatusUI({
            maritime: 'green', // Still simulated
            us_data: 'red',
            canada_data: 'red',
            integrity: 'red'
        });
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
                // Manually attach ID for zoomToGrid lookup
                layer.feature = { id: region.id };

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
                        <strong style="color:${getStyle(region.properties).color}">${(region.properties.risk_score * 100).toFixed(0)}/100</strong>
                    </div>
                    <div class="popup-row">
                        <span>Confidence:</span>
                        <span>${region.properties.confidence}</span>
                    </div>
                    <div style="margin-top:0.5rem; font-size:0.8rem; border-top:1px solid rgba(255,255,255,0.1); padding-top:0.25rem; line-height:1.4;">
                        <em>${region.properties.explanation}</em>
                    </div>
                    <div style="margin-top:0.5rem; font-size:0.7rem; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.25rem;">
                        <strong>Tracking Sources:</strong><br>
                        ${region.properties.citations
                        ? region.properties.citations.map(c => `<a href="${c.href}" target="_blank" rel="noopener" style="color:var(--primary-action); text-decoration:none;">${c.label} ↗</a>`).join('<br>')
                        : 'Model Inference Only'}
                    </div>
                `;
                layer.bindPopup(popupContent);
            }
        });

        // Attach ID to the group layer for easy lookup
        geoLayer.regionId = region.id;
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
            <ul style="padding-left:1rem; margin-bottom:0.75rem;">
                ${props.drivers.map(d => `<li>${d}</li>`).join('')}
            </ul>
            
            <div style="font-size: 0.75rem; color: #94a3b8; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.5rem;">
                <strong>Tracking Sources:</strong><br>
                ${props.citations
                ? props.citations.map(c => `<a href="${c.href}" target="_blank" rel="noopener" style="color:var(--primary-action); text-decoration:none; display:block; margin-top:2px;">${c.label} ↗</a>`).join('')
                : 'Model Inference Only'}
            </div>
        `;

        container.style.opacity = '1';
    }, 200);
}

function updateAlertsFeed(alerts) {
    const feedContainer = document.querySelector('.feed-container');
    if (!feedContainer) return;

    if (alerts.length === 0) {
        feedContainer.innerHTML = '<div class="feed-item">No active alerts. All systems nominal.</div>';
        return;
    }

    // Enrich alerts with clickable Grid links
    feedContainer.innerHTML = alerts.map(alert => {
        // Regex to find "grid-XXX" or "grid-XXX-can" and wrap in onclick
        const enrichedDetail = alert.detail.replace(
            /(grid-[\w-]+)/g,
            '<span class="grid-link" onclick="zoomToGrid(\'$1\')">$1</span>'
        );

        return `
        <div class="feed-item ${alert.type === 'CRITICAL' ? 'critical-alert' : ''}">
            <div class="feed-item-header">
                <strong class="feed-item-title">${alert.type}:</strong>
                <span class="feed-timestamp">${alert.timestamp}</span>
            </div>
            <div class="feed-content">
                <span class="${alert.type === 'CRITICAL' ? 'critical-highlight' : 'signal-highlight'}">${alert.title}</span><br>
                ${enrichedDetail}
            </div>
        </div>
    `}).join('');
}

// Global function for grid zooming
window.zoomToGrid = function (gridId) {
    if (!layerGroups.risk_overlay) return;

    let foundLayer = null;
    layerGroups.risk_overlay.eachLayer(layer => {
        // Check custom property attached to the L.geoJSON layer
        if (layer.regionId === gridId) {
            foundLayer = layer;
        }
    });

    if (foundLayer) {
        map.fitBounds(foundLayer.getBounds(), { padding: [50, 50], maxZoom: 10 });
        foundLayer.openPopup();
    } else {
        console.warn(`Grid ${gridId} not found on map.`);
    }
};

function updateStatusUI(health) {
    const mapping = {
        'maritime': 'dot-maritime',
        'us_data': 'dot-us',
        'canada_data': 'dot-canada',
        'integrity': 'dot-gbif',
        'infrastructure': 'dot-glfc'
    };

    Object.keys(health).forEach(key => {
        const dotId = mapping[key];
        const dot = document.getElementById(dotId);
        if (dot) {
            // Reset classes
            dot.className = 'status-row-dot';
            if (health[key] !== 'green') {
                dot.classList.add(health[key]);
            }
        }
    });

    updateMasterStatus();
}

function updateMasterStatus() {
    const mainLight = document.getElementById('status-light');
    const rowDots = document.querySelectorAll('.status-row-dot');

    let hasError = false;
    rowDots.forEach(dot => {
        if (dot.classList.contains('red')) hasError = true;
    });

    // Reset master light
    mainLight.className = 'status-dot';

    if (hasError) {
        mainLight.classList.add('yellow'); // Main goes yellow if any row is red
    }
}

// --- EXECUTE ---
loadAILayer();


/* =========================================================================
   4. INTERACTIVITY & TOGGLES
   ========================================================================= */

// Layer Toggles
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

// UI Collapsible Logic
function setupUIInteractivity() {
    // 1. Sidebar Toggle
    const sidebar = document.getElementById('main-sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebarIcon = sidebarToggle.querySelector('polyline');

    // 2. Status Board Toggle
    const statusBoard = document.getElementById('status-board');
    const statusToggle = document.getElementById('status-toggle');
    const statusIcon = statusToggle.querySelector('polyline');

    const togglePanel = (panel, icon, forceCollapse) => {
        const isCollapsed = forceCollapse !== undefined ? forceCollapse : !panel.classList.contains('collapsed');

        if (isCollapsed) {
            panel.classList.add('collapsed');
            icon.setAttribute('points', '6 9 12 15 18 9'); // Chevron Down
        } else {
            panel.classList.remove('collapsed');
            icon.setAttribute('points', '18 15 12 9 6 15'); // Chevron Up
        }
    };

    sidebarToggle.addEventListener('click', () => togglePanel(sidebar, sidebarIcon));
    statusToggle.addEventListener('click', () => togglePanel(statusBoard, statusIcon));

    // 3. Subsection Toggles (Sidebar Sections)
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', () => {
            const section = header.closest('.panel-section');
            section.classList.toggle('collapsed');
        });
    });

    // DEFAULT STATE ENFORCEMENT
    // Collapse all except 'Intelligence Feed' (bottom section)
    document.querySelectorAll('.panel-section').forEach(section => {
        if (section.id === 'feed-section') {
            section.classList.remove('collapsed');
        } else {
            section.classList.add('collapsed');
        }
    });

    // Mobile Check
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        togglePanel(sidebar, sidebarIcon, true);
        togglePanel(statusBoard, statusIcon, true);
    }

    // Auto-collapse logic: collapsed on small vertical viewports or mobile-width
    const handleResize = () => {
        const isSmallScreen = window.innerWidth <= 768 || window.innerHeight <= 700;

        if (isSmallScreen) {
            if (!sidebar.classList.contains('collapsed')) togglePanel(sidebar, sidebarIcon, true);
            if (!statusBoard.classList.contains('collapsed')) togglePanel(statusBoard, statusIcon, true);
        } else {
            // Keep user preference if possible, but for demo we can force open on large screens
            if (sidebar.classList.contains('collapsed')) togglePanel(sidebar, sidebarIcon, false);
            if (statusBoard.classList.contains('collapsed')) togglePanel(statusBoard, statusIcon, false);
        }
    };

    // Initialize
    handleResize();
    window.addEventListener('resize', handleResize);
}

// Master status logic update
function updateMasterStatus() {
    const masterLight = document.getElementById('master-status-light');
    const rowDots = document.querySelectorAll('.status-row-dot');

    let hasError = false;
    let hasWarning = false;

    rowDots.forEach(dot => {
        if (dot.classList.contains('red')) hasError = true;
        if (dot.classList.contains('yellow')) hasWarning = true;
    });

    // Update Text and Light
    if (masterLight) {
        const statusText = document.getElementById('status-text');
        masterLight.className = 'status-dot';

        if (hasError) {
            masterLight.classList.add('red');
            if (statusText) statusText.innerText = 'System Offline';
        } else if (hasWarning) {
            masterLight.classList.add('yellow');
            if (statusText) statusText.innerText = 'Syncing Data...';
        } else {
            masterLight.classList.add('active'); // Pulse green
            if (statusText) statusText.innerText = 'Live Model Connected';
        }
    }
}

// Ensure master status is updated after AI data loads
const originalUpdateStatusUI = updateStatusUI;
updateStatusUI = function (health) {
    originalUpdateStatusUI(health);
    updateMasterStatus();
};

// Landing Page Logic (Removed)

// Ensure landing page setup is called
document.addEventListener('DOMContentLoaded', () => {
    setupUIInteractivity();
    console.log("System Initialized: Invasive Species Intelligence v0.5");
});


