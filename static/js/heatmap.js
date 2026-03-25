/**
 * Smart Heatmap Visualization Module
 * Renders a real-time city traffic heatmap on canvas
 * with color coding: Green → Smooth, Yellow → Moderate, Red → Heavy
 */

let heatmapRefreshInterval = null;

function initHeatmapView() {
    loadHeatmapData();
    if (heatmapRefreshInterval) clearInterval(heatmapRefreshInterval);
    heatmapRefreshInterval = setInterval(loadHeatmapData, 5000);
}

function stopHeatmapRefresh() {
    if (heatmapRefreshInterval) {
        clearInterval(heatmapRefreshInterval);
        heatmapRefreshInterval = null;
    }
}

async function loadHeatmapData() {
    try {
        const res = await fetch('/api/heatmap/data/');
        const data = await res.json();
        drawHeatmap(data);
        renderHeatmapJunctionList(data);
    } catch (err) {
        console.error('Heatmap load error:', err);
        // Draw empty heatmap with demo data
        drawHeatmapDemo();
    }
}

function drawHeatmap(junctions) {
    const canvas = document.getElementById('heatmapCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 500;

    const w = canvas.width;
    const h = canvas.height;

    // Background
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, w, h);

    // Draw city grid
    drawCityGrid(ctx, w, h);

    // If no real junctions, draw demo
    if (!junctions || junctions.length === 0) {
        drawHeatmapDemo();
        return;
    }

    // Calculate positions (spread across canvas)
    const cols = Math.ceil(Math.sqrt(junctions.length));
    const rows = Math.ceil(junctions.length / cols);
    const cellW = w / (cols + 1);
    const cellH = h / (rows + 1);

    junctions.forEach((jn, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const cx = cellW * (col + 1);
        const cy = cellH * (row + 1);

        drawHeatmapNode(ctx, cx, cy, jn);
    });

    // Draw roads between junctions
    ctx.strokeStyle = 'rgba(100,100,150,0.3)';
    ctx.lineWidth = 20;
    ctx.setLineDash([]);

    for (let i = 0; i < junctions.length - 1; i++) {
        const col1 = i % cols, row1 = Math.floor(i / cols);
        const col2 = (i + 1) % cols, row2 = Math.floor((i + 1) / cols);
        const x1 = cellW * (col1 + 1), y1 = cellH * (row1 + 1);
        const x2 = cellW * (col2 + 1), y2 = cellH * (row2 + 1);

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
    }

    // Title
    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    ctx.font = 'bold 16px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('CITY TRAFFIC DENSITY MAP', 20, 30);

    // Timestamp
    ctx.font = '11px Inter, sans-serif';
    ctx.fillText(`Last updated: ${new Date().toLocaleTimeString()}`, 20, h - 15);
}

function drawCityGrid(ctx, w, h) {
    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 30) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 30) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
}

function drawHeatmapNode(ctx, cx, cy, junction) {
    const level = junction.congestion_level;
    let color, glowColor;

    if (level === 'heavy') {
        color = '#ef4444';
        glowColor = 'rgba(239, 68, 68, 0.4)';
    } else if (level === 'moderate') {
        color = '#eab308';
        glowColor = 'rgba(234, 179, 8, 0.3)';
    } else {
        color = '#22c55e';
        glowColor = 'rgba(34, 197, 94, 0.3)';
    }

    // Outer glow
    const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, 60);
    gradient.addColorStop(0, glowColor);
    gradient.addColorStop(1, 'transparent');
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(cx, cy, 60, 0, Math.PI * 2);
    ctx.fill();

    // Inner circle
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(cx, cy, 15, 0, Math.PI * 2);
    ctx.fill();

    // White border
    ctx.strokeStyle = 'rgba(255,255,255,0.5)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(cx, cy, 15, 0, Math.PI * 2);
    ctx.stroke();

    // Junction label
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(junction.code || junction.name, cx, cy - 22);

    // Vehicle count
    ctx.font = '10px Inter, sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.7)';
    ctx.fillText(`${junction.total_vehicles} vehicles`, cx, cy + 30);
}

function drawHeatmapDemo() {
    const canvas = document.getElementById('heatmapCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 500;

    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, w, h);
    drawCityGrid(ctx, w, h);

    // Demo junctions
    const demoJunctions = [
        { code: 'JN-001', name: 'Main St & 1st Ave', congestion_level: 'smooth', total_vehicles: 12 },
        { code: 'JN-002', name: 'Highway Exit 5', congestion_level: 'moderate', total_vehicles: 28 },
        { code: 'JN-003', name: 'Downtown Cross', congestion_level: 'heavy', total_vehicles: 45 },
        { code: 'JN-004', name: 'East Bridge', congestion_level: 'smooth', total_vehicles: 8 },
    ];

    const positions = [
        { x: w * 0.25, y: h * 0.3 },
        { x: w * 0.75, y: h * 0.3 },
        { x: w * 0.5, y: h * 0.6 },
        { x: w * 0.3, y: h * 0.75 },
    ];

    // Draw roads
    ctx.strokeStyle = 'rgba(100,100,150,0.3)';
    ctx.lineWidth = 15;
    for (let i = 0; i < positions.length - 1; i++) {
        ctx.beginPath();
        ctx.moveTo(positions[i].x, positions[i].y);
        ctx.lineTo(positions[i + 1].x, positions[i + 1].y);
        ctx.stroke();
    }
    // Connect back
    ctx.beginPath();
    ctx.moveTo(positions[3].x, positions[3].y);
    ctx.lineTo(positions[0].x, positions[0].y);
    ctx.stroke();

    demoJunctions.forEach((jn, i) => {
        drawHeatmapNode(ctx, positions[i].x, positions[i].y, jn);
    });

    ctx.fillStyle = 'rgba(255,255,255,0.3)';
    ctx.font = 'bold 16px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('CITY TRAFFIC DENSITY MAP (Demo)', 20, 30);

    ctx.font = '11px Inter, sans-serif';
    ctx.fillText('Add junctions via Admin panel for live data', 20, h - 15);
}

function renderHeatmapJunctionList(junctions) {
    const container = document.getElementById('heatmapJunctionList');
    if (!container) return;

    container.innerHTML = '';

    (junctions || []).forEach(jn => {
        const levelColors = { heavy: '#ef4444', moderate: '#eab308', smooth: '#22c55e' };
        const color = levelColors[jn.congestion_level] || '#888';

        const card = document.createElement('div');
        card.className = 'heatmap-junction-card glass-panel';
        card.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px;">
                <div class="heatmap-status-dot" style="background:${color};"></div>
                <div>
                    <strong>${jn.name}</strong>
                    <span class="junction-code">${jn.code}</span>
                </div>
            </div>
            <div style="display:flex; gap:20px; align-items:center;">
                <span>${jn.total_vehicles} vehicles</span>
                <span style="color:${color}; text-transform:capitalize; font-weight:600;">${jn.congestion_level}</span>
            </div>
        `;
        container.appendChild(card);
    });
}
