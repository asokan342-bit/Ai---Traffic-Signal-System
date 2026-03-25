// ============================================================
// ENVIRONMENT TRACKING MODULE
// ============================================================

let aqiTrendChartInstance = null;
let pollutantCompChartInstance = null;
let pollutantPieChartInstance = null;

// ── Init ──
window.initEnvironmentView = async function () {
    try {
        const data = await fetchPollutionLatest();
        const history = await fetchPollutionHistory();

        if (data && data.length > 0) {
            renderSummaryCards(data);
            renderJunctionCards(data);
            renderPollutantCompChart(data);
            renderPollutantPieChart(data);
        } else {
            // Show empty state
            const grid = document.getElementById('envJunctionGrid');
            if (grid) grid.innerHTML = '<p style="color:var(--text-secondary);">No pollution data available. Click "Generate Sample Data" to create readings.</p>';
        }

        if (history && history.length > 0) {
            renderAqiTrendChart(history);
        }

    } catch (e) {
        console.error('Environment view init error:', e);
    }
};

// ── API Calls ──
async function fetchPollutionLatest() {
    try {
        const res = await fetch('/api/pollution/latest/');
        if (res.ok) return await res.json();
        return [];
    } catch (e) {
        console.error('Failed to fetch pollution latest:', e);
        return [];
    }
}

async function fetchPollutionHistory() {
    try {
        const res = await fetch('/api/pollution/history/');
        if (res.ok) return await res.json();
        return [];
    } catch (e) {
        console.error('Failed to fetch pollution history:', e);
        return [];
    }
}

// ── Simulate Pollution Data ──
window.simulatePollutionData = async function () {
    try {
        const res = await fetch('/api/pollution/simulate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        if (res.ok) {
            const result = await res.json();
            if (typeof showNotification === 'function') {
                showNotification('Environment', result.message || 'Pollution data generated!', 'success');
            }
            // Refresh view
            initEnvironmentView();
        } else {
            console.error('Simulation failed:', res.status);
        }
    } catch (e) {
        console.error('Simulate pollution error:', e);
    }
};

// ── Summary Cards ──
function renderSummaryCards(data) {
    // Calculate averages across all junctions
    let totalAqi = 0, totalPm25 = 0, totalPm10 = 0, totalCo = 0, totalNo2 = 0;
    data.forEach(d => {
        totalAqi += d.aqi || 0;
        totalPm25 += d.pm25 || 0;
        totalPm10 += d.pm10 || 0;
        totalCo += d.co_level || 0;
        totalNo2 += d.no2_level || 0;
    });
    const count = data.length;
    const avgAqi = Math.round(totalAqi / count);
    const avgPm25 = (totalPm25 / count).toFixed(1);
    const avgPm10 = (totalPm10 / count).toFixed(1);
    const avgCo = (totalCo / count).toFixed(2);
    const avgNo2 = (totalNo2 / count).toFixed(2);

    // Update AQI gauge
    const aqiValueEl = document.getElementById('envAqiValue');
    const aqiLabelEl = document.getElementById('envAqiLabel');
    const aqiRingEl = document.getElementById('envAqiRing');
    const aqiCardEl = document.getElementById('envAqiCard');

    if (aqiValueEl) aqiValueEl.innerText = avgAqi;

    const { label, color, bgColor } = getAqiInfo(avgAqi);
    if (aqiLabelEl) {
        aqiLabelEl.innerText = label;
        aqiLabelEl.style.background = bgColor;
        aqiLabelEl.style.color = color;
    }
    if (aqiRingEl) {
        const pct = Math.min(100, (avgAqi / 500) * 100);
        aqiRingEl.style.background = `conic-gradient(${color} ${pct}%, rgba(255,255,255,0.05) ${pct}%)`;
    }
    if (aqiCardEl) {
        aqiCardEl.style.borderColor = color;
    }

    // Update pollutant cards
    const pm25El = document.getElementById('envPm25');
    if (pm25El) pm25El.innerText = avgPm25;

    const pm10El = document.getElementById('envPm10');
    if (pm10El) pm10El.innerText = avgPm10;

    const coEl = document.getElementById('envCo');
    if (coEl) coEl.innerText = avgCo;

    const no2El = document.getElementById('envNo2');
    if (no2El) no2El.innerText = avgNo2;

    // Update dashboard pollution widget
    const pollAqi = document.getElementById('pollutionAqi');
    const pollLabel = document.getElementById('pollutionLabel');
    const pollWidget = document.getElementById('pollutionWidget');
    if (pollAqi) pollAqi.innerText = `AQI: ${avgAqi}`;
    if (pollLabel) {
        pollLabel.innerText = label;
        pollLabel.style.color = color;
    }
    if (pollWidget) {
        pollWidget.style.borderColor = color;
        pollWidget.style.display = 'flex';
    }
}

// ── AQI Info Helper ──
function getAqiInfo(aqi) {
    if (aqi <= 50) return { label: 'Good', color: '#22c55e', bgColor: 'rgba(34,197,94,0.15)' };
    if (aqi <= 100) return { label: 'Moderate', color: '#eab308', bgColor: 'rgba(234,179,8,0.15)' };
    if (aqi <= 150) return { label: 'Unhealthy (Sensitive)', color: '#f97316', bgColor: 'rgba(249,115,22,0.15)' };
    if (aqi <= 200) return { label: 'Unhealthy', color: '#ef4444', bgColor: 'rgba(239,68,68,0.15)' };
    if (aqi <= 300) return { label: 'Very Unhealthy', color: '#a855f7', bgColor: 'rgba(168,85,247,0.15)' };
    return { label: 'Hazardous', color: '#991b1b', bgColor: 'rgba(153,27,27,0.2)' };
}

// ── Junction Cards ──
function renderJunctionCards(data) {
    const grid = document.getElementById('envJunctionGrid');
    if (!grid) return;

    if (!data || data.length === 0) {
        grid.innerHTML = '<p style="color:var(--text-secondary);">No pollution data available.</p>';
        return;
    }

    grid.innerHTML = data.map(d => {
        const { label, color, bgColor } = getAqiInfo(d.aqi);
        const timeStr = d.timestamp ? new Date(d.timestamp).toLocaleTimeString() : '--';

        return `
        <div class="env-junction-card glass-panel">
            <div class="env-junction-header">
                <h4><i class="fa-solid fa-location-dot" style="color:${color}"></i> ${d.junction_name || 'Junction'}</h4>
                <span class="quality-badge" style="background:${bgColor}; color:${color};">${label}</span>
            </div>
            <div class="env-junction-aqi" style="color:${color};">
                <span class="env-aqi-big">${d.aqi}</span>
                <span class="env-aqi-unit">AQI</span>
            </div>
            <div class="env-pollutant-grid">
                <div class="env-pollutant-item">
                    <span class="env-pollutant-label">PM2.5</span>
                    <span class="env-pollutant-value">${(d.pm25 || 0).toFixed(1)}</span>
                </div>
                <div class="env-pollutant-item">
                    <span class="env-pollutant-label">PM10</span>
                    <span class="env-pollutant-value">${(d.pm10 || 0).toFixed(1)}</span>
                </div>
                <div class="env-pollutant-item">
                    <span class="env-pollutant-label">CO</span>
                    <span class="env-pollutant-value">${(d.co_level || 0).toFixed(2)}</span>
                </div>
                <div class="env-pollutant-item">
                    <span class="env-pollutant-label">NO₂</span>
                    <span class="env-pollutant-value">${(d.no2_level || 0).toFixed(2)}</span>
                </div>
            </div>
            <div class="env-junction-footer">
                <i class="fa-regular fa-clock"></i> ${timeStr}
            </div>
        </div>`;
    }).join('');
}

// ── AQI Trend Chart ──
function renderAqiTrendChart(history) {
    const canvas = document.getElementById('aqiTrendChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (aqiTrendChartInstance) aqiTrendChartInstance.destroy();

    const labels = history.map(h => {
        const d = new Date(h.timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });
    const aqiData = history.map(h => h.aqi);

    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.3)');
    gradient.addColorStop(1, 'rgba(34, 197, 94, 0.0)');

    aqiTrendChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'AQI',
                data: aqiData,
                borderColor: '#22c55e',
                backgroundColor: gradient,
                borderWidth: 2.5,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#22c55e',
                pointRadius: 3,
                pointHoverRadius: 6,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 500,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', maxTicksLimit: 12 }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(34,197,94,0.3)',
                    borderWidth: 1,
                    callbacks: {
                        label: ctx => `AQI: ${ctx.parsed.y}`
                    }
                }
            }
        }
    });
}

// ── Pollutant Comparison Chart (Bar) ──
function renderPollutantCompChart(data) {
    const canvas = document.getElementById('pollutantCompChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (pollutantCompChartInstance) pollutantCompChartInstance.destroy();

    const labels = data.map(d => d.junction_name || 'Junction');

    pollutantCompChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'PM2.5',
                    data: data.map(d => d.pm25 || 0),
                    backgroundColor: 'rgba(167,139,250,0.7)',
                    borderRadius: 4
                },
                {
                    label: 'PM10',
                    data: data.map(d => d.pm10 || 0),
                    backgroundColor: 'rgba(96,165,250,0.7)',
                    borderRadius: 4
                },
                {
                    label: 'CO',
                    data: data.map(d => d.co_level || 0),
                    backgroundColor: 'rgba(251,191,36,0.7)',
                    borderRadius: 4
                },
                {
                    label: 'NO₂',
                    data: data.map(d => d.no2_level || 0),
                    backgroundColor: 'rgba(248,113,113,0.7)',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { position: 'top', labels: { color: '#aaa', padding: 10 } }
            }
        }
    });
}

// ── Pollutant Distribution (Pie/Doughnut) ──
function renderPollutantPieChart(data) {
    const canvas = document.getElementById('pollutantPieChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    if (pollutantPieChartInstance) pollutantPieChartInstance.destroy();

    // Aggregate all pollutants
    let totals = { pm25: 0, pm10: 0, co: 0, no2: 0 };
    data.forEach(d => {
        totals.pm25 += d.pm25 || 0;
        totals.pm10 += d.pm10 || 0;
        totals.co += d.co_level || 0;
        totals.no2 += d.no2_level || 0;
    });

    pollutantPieChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['PM2.5', 'PM10', 'CO', 'NO₂'],
            datasets: [{
                data: [totals.pm25, totals.pm10, totals.co, totals.no2],
                backgroundColor: [
                    'rgba(167,139,250,0.8)',
                    'rgba(96,165,250,0.8)',
                    'rgba(251,191,36,0.8)',
                    'rgba(248,113,113,0.8)'
                ],
                borderWidth: 0,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#aaa', padding: 12, font: { size: 13 } }
                }
            }
        }
    });
}
