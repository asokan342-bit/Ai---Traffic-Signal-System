/**
 * Enhanced Analytics Module
 * Handles daily/weekly/monthly reports, efficiency metrics,
 * PDF export, and historical trend prediction charts.
 */

let currentAnalyticsPeriod = 'daily';
let trendChart = null;
let reportVolumeChart = null;

async function initAnalyticsView() {
    loadEfficiencyMetrics();
    loadAnalyticsPeriod('daily');
    loadTrendPrediction();
}

async function loadEfficiencyMetrics() {
    try {
        const res = await fetch('/api/analytics/efficiency_stats/');
        const data = await res.json();

        document.getElementById('analyticsAvgWait').textContent = (data.average_waiting_time || 0) + 's';
        document.getElementById('analyticsThroughput').textContent = (data.vehicle_throughput_rate || 0) + '%';
        document.getElementById('analyticsEmergResponse').textContent = (data.emergency_response_time || 0) + 's';
        document.getElementById('analyticsEfficiency').textContent = (data.signal_efficiency || 0) + '%';
    } catch (err) {
        console.error('Efficiency metrics error:', err);
    }
}

async function loadAnalyticsPeriod(period, tabEl) {
    currentAnalyticsPeriod = period;

    // Update tab active state
    if (tabEl) {
        const tabs = tabEl.parentElement.querySelectorAll('.dir-tab');
        tabs.forEach(t => t.classList.remove('active'));
        tabEl.classList.add('active');
    }

    const reportContainer = document.getElementById('reportTableContainer');
    const reportTitle = document.getElementById('reportTitle');

    try {
        let data;
        if (period === 'daily') {
            const res = await fetch('/api/analytics/daily_report/');
            data = await res.json();
            reportTitle.innerHTML = '<i class="fa-solid fa-calendar-day"></i> Daily Report — ' + (data.date || 'Today');

            let tableHTML = `
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Direction</th>
                            <th>Total Vehicles</th>
                            <th>Avg Wait (s)</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            (data.directions || []).forEach(d => {
                tableHTML += `<tr><td>${d.name}</td><td>${d.total_vehicles}</td><td>${d.avg_wait}</td></tr>`;
            });
            tableHTML += `</tbody></table>`;
            tableHTML += `
                <div class="report-summary-row">
                    <span>Total: <strong>${data.total_vehicles}</strong> vehicles</span>
                    <span>Passed: <strong>${data.vehicles_passed}</strong></span>
                    <span>Emergencies: <strong>${data.emergency_events}</strong></span>
                </div>
            `;
            reportContainer.innerHTML = tableHTML;

        } else if (period === 'weekly') {
            const res = await fetch('/api/analytics/weekly_report/');
            data = await res.json();
            reportTitle.innerHTML = `<i class="fa-solid fa-calendar-week"></i> Weekly Report — ${data.week_start} to ${data.week_end}`;

            let tableHTML = `
                <table class="history-table">
                    <thead>
                        <tr><th>Day</th><th>Date</th><th>Total Vehicles</th><th>Avg Wait (s)</th><th>Emergencies</th></tr>
                    </thead>
                    <tbody>
            `;
            (data.daily_data || []).forEach(d => {
                tableHTML += `<tr><td>${d.day_name}</td><td>${d.date}</td><td>${d.total_vehicles}</td><td>${d.avg_wait}</td><td>${d.emergencies}</td></tr>`;
            });
            tableHTML += `</tbody></table>`;
            reportContainer.innerHTML = tableHTML;

            // Build weekly chart
            buildWeeklyChart(data.daily_data || []);

        } else if (period === 'monthly') {
            const res = await fetch('/api/analytics/monthly_report/');
            data = await res.json();
            reportTitle.innerHTML = `<i class="fa-solid fa-calendar"></i> Monthly Report — ${data.month}`;

            let tableHTML = `
                <table class="history-table">
                    <thead>
                        <tr><th>Week</th><th>Start</th><th>End</th><th>Total Vehicles</th></tr>
                    </thead>
                    <tbody>
            `;
            (data.weekly_breakdown || []).forEach(w => {
                tableHTML += `<tr><td>Week ${w.week}</td><td>${w.start}</td><td>${w.end}</td><td>${w.total_vehicles}</td></tr>`;
            });
            tableHTML += `</tbody></table>`;
            tableHTML += `
                <div class="report-summary-row">
                    <span>Total: <strong>${data.total_vehicles}</strong> vehicles</span>
                    <span>Passed: <strong>${data.vehicles_passed}</strong></span>
                    <span>Avg Wait: <strong>${data.avg_waiting_time}s</strong></span>
                    <span>Emergencies: <strong>${data.emergency_events}</strong></span>
                </div>
            `;
            reportContainer.innerHTML = tableHTML;
        }

    } catch (err) {
        console.error('Analytics period load error:', err);
        reportContainer.innerHTML = '<p style="color:var(--text-secondary);">Failed to load report data.</p>';
    }
}

function buildWeeklyChart(dailyData) {
    const canvas = document.getElementById('trendPredictionChart');
    if (!canvas) return;

    if (reportVolumeChart) reportVolumeChart.destroy();

    const labels = dailyData.map(d => d.day_name);
    const vehicles = dailyData.map(d => d.total_vehicles);
    const waits = dailyData.map(d => d.avg_wait);

    reportVolumeChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Vehicles',
                    data: vehicles,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                },
                {
                    label: 'Avg Wait (s)',
                    data: waits,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4,
                    yAxisID: 'y1',
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: '#aaa' } },
            },
            scales: {
                x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y1: {
                    position: 'right',
                    ticks: { color: '#888' },
                    grid: { display: false },
                }
            }
        }
    });
}

async function loadTrendPrediction() {
    try {
        // Use weekly data for trend prediction
        const res = await fetch('/api/analytics/weekly_report/');
        const data = await res.json();

        const dailyData = data.daily_data || [];
        if (dailyData.length === 0) return;

        const canvas = document.getElementById('trendPredictionChart');
        if (!canvas) return;

        if (trendChart) trendChart.destroy();

        const labels = dailyData.map(d => d.day_name);
        const vehicles = dailyData.map(d => d.total_vehicles);

        // Simple Moving Average prediction (next 3 days)
        const sma = [];
        const windowSize = 3;
        for (let i = 0; i < vehicles.length; i++) {
            if (i < windowSize - 1) {
                sma.push(null);
            } else {
                const window = vehicles.slice(i - windowSize + 1, i + 1);
                sma.push(Math.round(window.reduce((a, b) => a + b, 0) / windowSize));
            }
        }

        // Predict next 3 days
        const lastSMA = sma.filter(v => v !== null);
        const trend = lastSMA.length >= 2 ? lastSMA[lastSMA.length - 1] - lastSMA[lastSMA.length - 2] : 0;

        const predLabels = ['Day +1', 'Day +2', 'Day +3'];
        const predValues = [];
        let lastVal = vehicles[vehicles.length - 1] || 0;
        for (let i = 0; i < 3; i++) {
            lastVal = Math.max(0, lastVal + trend + Math.round(Math.random() * 5 - 2));
            predValues.push(lastVal);
        }

        const allLabels = [...labels, ...predLabels];
        const actualData = [...vehicles, null, null, null];
        const predData = [...new Array(vehicles.length).fill(null), ...predValues];
        const smaData = [...sma, null, null, null];

        trendChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: 'Actual',
                        data: actualData,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    },
                    {
                        label: 'Prediction',
                        data: predData,
                        borderColor: '#a855f7',
                        backgroundColor: 'rgba(168, 85, 247, 0.1)',
                        borderDash: [5, 5],
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                    },
                    {
                        label: 'Moving Avg',
                        data: smaData,
                        borderColor: '#eab308',
                        borderDash: [3, 3],
                        fill: false,
                        tension: 0.4,
                        pointRadius: 2,
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { labels: { color: '#aaa' } },
                    title: { display: false }
                },
                scales: {
                    x: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#888' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                }
            }
        });

    } catch (err) {
        console.error('Trend prediction error:', err);
    }
}

async function exportPDF() {
    try {
        showNotification('Generating PDF', 'Please wait while the report is generated...', 'info');

        const res = await fetch('/api/analytics/export_pdf/');

        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `traffic_report_${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            showNotification('PDF Ready', 'Report downloaded successfully!', 'success');
        } else {
            const err = await res.json();
            showNotification('PDF Error', err.error || 'Failed to generate PDF', 'danger');
        }
    } catch (err) {
        showNotification('PDF Error', 'Network error generating report.', 'danger');
    }
}
