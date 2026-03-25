/**
 * Emergency Monitoring Module
 * Handles live ambulance GPS tracking, emergency status display,
 * clearance stats, and emergency history table.
 */

let emergencyRefreshInterval = null;

function initEmergencyView() {
    loadEmergencyData();
    loadEmergencyHistory();
    // Auto-refresh every 3 seconds
    if (emergencyRefreshInterval) clearInterval(emergencyRefreshInterval);
    emergencyRefreshInterval = setInterval(() => {
        loadEmergencyData();
    }, 3000);
}

function stopEmergencyRefresh() {
    if (emergencyRefreshInterval) {
        clearInterval(emergencyRefreshInterval);
        emergencyRefreshInterval = null;
    }
}

async function loadEmergencyData() {
    try {
        // Live emergency data
        const liveRes = await fetch('/api/emergency/live/');
        const liveData = await liveRes.json();

        // Emergency stats
        const statsRes = await fetch('/api/analytics/emergency_stats/');
        const statsData = await statsRes.json();

        // Update status badge
        const badge = document.getElementById('emergencyStatusBadge');
        const banner = document.getElementById('emergencyBanner');

        if (liveData.emergency_mode) {
            badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> EMERGENCY ACTIVE';
            badge.className = 'emergency-status-badge emergency-active';
            banner.style.display = 'flex';
        } else {
            badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> System Normal';
            badge.className = 'emergency-status-badge emergency-normal';
            banner.style.display = 'none';
        }

        // Update active emergency info
        const infoEl = document.getElementById('activeEmergencyInfo');
        if (liveData.active_emergencies && liveData.active_emergencies.length > 0) {
            const emerg = liveData.active_emergencies[0];
            infoEl.innerHTML = `
                <div class="emergency-info-card">
                    <div class="info-row"><strong>Direction:</strong> ${emerg.signal_direction}</div>
                    <div class="info-row"><strong>Junction:</strong> ${emerg.junction_name || 'N/A'}</div>
                    <div class="info-row"><strong>Ambulance:</strong> ${emerg.ambulance_id || 'Unknown'}</div>
                    <div class="info-row"><strong>Started:</strong> ${new Date(emerg.start_time).toLocaleTimeString()}</div>
                    <div class="info-row" style="color:var(--neon-red);"><strong>Status:</strong> 🚨 ACTIVE</div>
                </div>
            `;
            // Draw ambulance on map
            drawAmbulanceMap(liveData.active_emergencies);
        } else {
            infoEl.innerHTML = '<p style="color:var(--text-secondary);">No active emergency.</p>';
            drawAmbulanceMap([]);
        }

        // Update stats
        document.getElementById('emergTotalEvents').textContent = statsData.total_emergencies || 0;
        document.getElementById('emergAvgClearance').textContent = (statsData.avg_clearance_time || 0) + 's';
        document.getElementById('emergResolved').textContent = statsData.resolved || 0;

    } catch (err) {
        console.error('Emergency data load error:', err);
    }
}

function drawAmbulanceMap(emergencies) {
    const canvas = document.getElementById('ambulanceMapCanvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight || 350;

    const w = canvas.width;
    const h = canvas.height;

    // Dark background
    ctx.fillStyle = '#0a0a1a';
    ctx.fillRect(0, 0, w, h);

    // Draw grid
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = 1;
    for (let x = 0; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 0; y < h; y += 40) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }

    // Draw roads (crosshair pattern)
    ctx.fillStyle = 'rgba(50,50,80,0.5)';
    ctx.fillRect(w * 0.4, 0, w * 0.2, h);  // Vertical road
    ctx.fillRect(0, h * 0.4, w, h * 0.2);  // Horizontal road

    // Center intersection
    ctx.fillStyle = 'rgba(100,100,150,0.3)';
    ctx.fillRect(w * 0.4, h * 0.4, w * 0.2, h * 0.2);

    // Direction labels
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '12px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('NORTH', w / 2, 20);
    ctx.fillText('SOUTH', w / 2, h - 10);
    ctx.save();
    ctx.translate(15, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('WEST', 0, 0);
    ctx.restore();
    ctx.save();
    ctx.translate(w - 15, h / 2);
    ctx.rotate(Math.PI / 2);
    ctx.fillText('EAST', 0, 0);
    ctx.restore();

    // Draw ambulances
    emergencies.forEach((emerg, i) => {
        // Simulate position based on direction
        let ax, ay;
        const dir = emerg.signal_direction;
        const t = (Date.now() / 1000) % 10 / 10; // Animation factor

        if (dir === 'North') { ax = w / 2; ay = h * 0.1 + t * h * 0.3; }
        else if (dir === 'South') { ax = w / 2; ay = h * 0.9 - t * h * 0.3; }
        else if (dir === 'East') { ax = w * 0.9 - t * w * 0.3; ay = h / 2; }
        else { ax = w * 0.1 + t * w * 0.3; ay = h / 2; }

        // Ambulance glow
        const gradient = ctx.createRadialGradient(ax, ay, 0, ax, ay, 30);
        gradient.addColorStop(0, 'rgba(239, 68, 68, 0.6)');
        gradient.addColorStop(1, 'rgba(239, 68, 68, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(ax - 30, ay - 30, 60, 60);

        // Ambulance icon (cross)
        ctx.fillStyle = '#ef4444';
        ctx.fillRect(ax - 8, ay - 3, 16, 6);
        ctx.fillRect(ax - 3, ay - 8, 6, 16);

        // Label
        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(emerg.ambulance_id || '🚑', ax, ay - 15);
    });

    // Center label
    ctx.fillStyle = 'rgba(255,255,255,0.2)';
    ctx.font = 'bold 14px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('JUNCTION', w / 2, h / 2 + 5);
}

async function loadEmergencyHistory() {
    try {
        const res = await fetch('/api/emergency/history/');
        const data = await res.json();
        const tbody = document.getElementById('emergencyHistoryBody');
        if (!tbody) return;

        tbody.innerHTML = '';
        (data.results || []).forEach(log => {
            const row = document.createElement('tr');
            const statusClass = log.resolved ? 'state-badge-green' : 'state-badge-red';
            const statusText = log.resolved ? 'Resolved' : 'Active';
            row.innerHTML = `
                <td>${new Date(log.start_time).toLocaleString()}</td>
                <td>${log.signal_direction || '--'}</td>
                <td>${log.ambulance_id || '--'}</td>
                <td>${log.clearance_time || 0}</td>
                <td>${Math.round(log.duration_seconds || 0)}</td>
                <td><span class="${statusClass}">${statusText}</span></td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error('Emergency history load error:', err);
    }
}
