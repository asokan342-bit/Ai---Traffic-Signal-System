// analytics.js

document.addEventListener('DOMContentLoaded', () => {
    loadAllAnalytics();
});

const DIRECTIONS = ['N', 'S', 'E', 'W'];
const charts = {}; // Store chart instances

async function loadAllAnalytics() {
    for (const dir of DIRECTIONS) {
        await loadDirectionAnalytics(dir);
    }
}

async function loadDirectionAnalytics(direction) {
    try {
        // 1. Fetch Summary for High-level stats
        const summaryRes = await fetch(`/api/analytics/direction/${direction}/summary/?format=json`);
        const summary = await summaryRes.json();

        // 2. Fetch Insights for Peak Time
        const insightsRes = await fetch(`/api/analytics/direction/${direction}/insights/?format=json`);
        const insights = await insightsRes.json();

        // 3. Fetch Charts Data for Pie Chart
        const chartsRes = await fetch(`/api/analytics/direction/${direction}/charts/?format=json`);
        const chartData = await chartsRes.json();

        // --- UPDATE UI ---

        // Stats
        setText(`total-${direction}`, summary.total_vehicles || '0');
        setText(`peak-${direction}`, insights.peak_rush_hour || 'N/A');
        setText(`health-${direction}`, summary.congestion_level || 'Unknown');

        // Color code health badge
        const badge = document.getElementById(`health-${direction}`);
        if (badge) {
            const level = summary.congestion_level;
            if (level === 'Critical') badge.style.color = '#ef4444'; // Red
            else if (level === 'Heavy') badge.style.color = '#f59e0b'; // Amber
            else badge.style.color = '#22c55e'; // Green
            badge.style.background = `rgba(${level === 'Critical' ? '239, 68, 68' : (level === 'Heavy' ? '245, 158, 11' : '34, 197, 94')}, 0.1)`;
        }

        // Render Pie Chart
        renderDirectionPie(direction, chartData.distribution_chart);

    } catch (e) {
        console.error(`Error loading analytics for ${direction}:`, e);
    }
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function renderDirectionPie(direction, data) {
    const ctx = document.getElementById(`chart-${direction}`).getContext('2d');

    if (charts[direction]) {
        charts[direction].destroy();
    }

    charts[direction] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels, // ['2-Wheelers', '4-Wheelers', etc.]
            datasets: [{
                data: data.data,
                backgroundColor: [
                    '#3b82f6', // 2W - Blue
                    '#8b5cf6', // 4W - Violet
                    '#f59e0b', // Heavy - Amber
                    '#ef4444'  // Emergency - Red
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%', // Thinner doughnut
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { size: 10 },
                        boxWidth: 10,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }
            }
        }
    });
}
