// ============================================================
// GLOBAL VARIABLES
// ============================================================

let vehicleExtra = {
    N: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    S: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    E: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } },
    W: { crossed: 0, lastCrossed: 0, passed_breakdown: { bike: 0, car: 0, truck: 0, emergency: 0 } }
};

let simulationActive = false;
let updateInterval = 1000;
let signalData = {};
let simulationIntervalId = null;

// ============================================================
// API FUNCTIONS
// ============================================================

async function fetchSignals() {
    try {
        const response = await fetch('/api/signals/all_signals/');
        const data = await response.json();
        return data;
    } catch (error) {
        addLog('❌ Failed to fetch signals');
        return [];
    }
}

async function updateVehicleCount(direction, vehicleCounts) {
    // vehicleCounts = { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 }
    const signal = signalData[direction];
    if (!signal) return;

    try {
        const response = await fetch(
            `/api/signals/${signal.id}/update_vehicle_count/`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify(vehicleCounts)
            }
        );

        const data = await response.json();
        signalData[direction] = data;
        updateAllControls([data]);
        return data;
    } catch {
        addLog('❌ Vehicle update failed');
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// ============================================================
// UI FUNCTIONS
// ============================================================

function createSignalControl(signal) {
    const directions = { N: 'NORTH', S: 'SOUTH', E: 'EAST', W: 'WEST' };
    const icons = { N: 'fa-arrow-up', S: 'fa-arrow-down', E: 'fa-arrow-right', W: 'fa-arrow-left' };
    const state = signal.current_state;
    const isEmergency = signal.is_emergency_active;

    // Status Classes
    let activeClass = '';
    if (state === 'GREEN') activeClass = 'active-green';
    if (state === 'RED') activeClass = 'active-red';
    if (state === 'YELLOW') activeClass = 'active-yellow';
    if (isEmergency) activeClass = 'emergency-mode';

    // Timer calc (simplistic)
    let timeColor = '#fff';
    if (state === 'GREEN') timeColor = 'var(--neon-green)';
    if (state === 'RED') timeColor = 'var(--neon-red)';

    // NEW CARD TEMPLATE
    return `
    <div class="control-card ${activeClass}" id="control-${signal.direction}">
        <!-- HEADER -->
        <div class="card-header">
            <div class="header-left">
                <div class="status-dot" id="dot-${signal.direction}" style="background: ${state === 'GREEN' ? 'var(--neon-green)' : (state === 'RED' ? 'var(--neon-red)' : 'var(--neon-yellow)')}; box-shadow: 0 0 5px ${state === 'GREEN' ? 'var(--neon-green)' : (state === 'RED' ? 'var(--neon-red)' : 'var(--neon-yellow)')}"></div>
                <div class="direction-title">
                    <i class="fa-solid ${icons[signal.direction]} direction-icon"></i>
                    ${directions[signal.direction]}
                </div>
            </div>
            <div class="status-text" id="status-text-${signal.direction}" style="color: ${state === 'GREEN' ? 'var(--neon-green)' : (state === 'RED' ? 'var(--neon-red)' : 'var(--neon-yellow)')}">
                ${state}
                ${isEmergency ? ' <i class="fa-solid fa-truck-medical fa-beat" style="color:#ef4444;"></i>' : ''}
            </div>
        </div>

        <!-- STATS GRID -->
        <div class="card-stats-row">
            <!-- Col 1: Counts -->
            <div class="stats-group">
                <div class="stats-item">
                    <i class="fa-solid fa-car-side"></i>
                    <span class="stats-value" id="count-${signal.direction}">${signal.vehicle_count}</span>
                    <span class="stats-label">Count</span>
                </div>
                <div class="stats-item">
                    <i class="fa-regular fa-clock"></i>
                    <span class="stats-value timer-active" id="time-${signal.direction}" style="color:${timeColor}">--</span>
                    <span class="stats-label">Time</span>
                </div>
            </div>

            <!-- Col 2: Score -->
            <div class="stats-group">
                <div class="stats-item">
                    <i class="fa-solid fa-weight-hanging"></i>
                    <span class="stats-value highlight-score" id="score-${signal.direction}">
                        ${signal.current_weighted_density ? signal.current_weighted_density.toFixed(1) : '0.0'}
                    </span>
                    <span class="stats-label">Score</span>
                </div>
                <div class="stats-item">
                   <div class="max-time">(Max: ${signal.green_time}s)</div>
                </div>
            </div>
        </div>

        <!-- VEHICLE CONTROLS (+1) -->
        <div class="vehicle-controls">
            <button onclick="addVehicle('${signal.direction}', 'bike')" class="btn-add-vehicle" title="Add Bike">
                <i class="fa-solid fa-motorcycle"></i> +1
            </button>
            <button onclick="addVehicle('${signal.direction}', 'car')" class="btn-add-vehicle" title="Add Car">
                <i class="fa-solid fa-car"></i> +1
            </button>
            <button onclick="addVehicle('${signal.direction}', 'truck')" class="btn-add-vehicle" title="Add Truck">
                <i class="fa-solid fa-truck"></i> +1
            </button>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="action-buttons">
            <button onclick="triggerEmergency('${signal.direction}')" id="sos-btn-${signal.direction}" class="btn-action btn-sos ${isEmergency ? 'active' : ''}">
                <i class="fa-solid fa-truck-medical"></i> SOS
            </button>
            <button onclick="showDirectionDetails('${signal.direction}')" class="btn-action btn-details">
                <i class="fa-solid fa-chart-bar"></i> Details
            </button>
        </div>
    </div>
    `;
}

function updateAllControls(signals) {
    const panel = document.getElementById('signalControls');

    signals.forEach(s => {
        signalData[s.direction] = s;

        // Check if card exists
        const cardId = `control-${s.direction}`;
        let card = document.getElementById(cardId);

        if (!card) {
            // Create new if missing
            panel.innerHTML += createSignalControl(s);
        } else {
            // Update existing in-place

            let stateColor = '#ccc';
            if (s.current_state === 'GREEN') stateColor = 'var(--neon-green)';
            if (s.current_state === 'RED') stateColor = 'var(--neon-red)';
            if (s.current_state === 'YELLOW') stateColor = 'var(--neon-yellow)';

            const isEmergency = s.is_emergency_active;
            const density = s.current_weighted_density ? s.current_weighted_density.toFixed(1) : '0.0';

            // 1. Update DOT
            const dot = document.getElementById(`dot-${s.direction}`);
            if (dot) {
                dot.style.background = stateColor;
                dot.style.boxShadow = `0 0 10px ${stateColor}`;
            }

            // 2. Update Status Text
            const statusText = document.getElementById(`status-text-${s.direction}`);
            if (statusText) {
                statusText.innerHTML = `${s.current_state} ${isEmergency ? ' <i class="fa-solid fa-truck-medical fa-beat" style="color:#ef4444;"></i>' : ''}`;
                statusText.style.color = stateColor;
            }

            // 3. Update Counts
            const countEl = document.getElementById(`count-${s.direction}`);
            if (countEl) countEl.innerText = s.vehicle_count;

            // 4. Update Score
            const scoreEl = document.getElementById(`score-${s.direction}`);
            if (scoreEl) scoreEl.innerText = density;

            // 5. Update SOS Button State
            const sosBtn = document.getElementById(`sos-btn-${s.direction}`);
            if (sosBtn) {
                if (isEmergency) sosBtn.classList.add('active');
                else sosBtn.classList.remove('active');
            }

            // 6. Calculate Time Remaining
            if (s.state_start_time) {
                const now = new Date();
                const start = new Date(s.state_start_time);
                const elapsed = (now - start) / 1000;

                let duration = 0;
                if (s.current_state === 'GREEN') duration = s.green_time;
                else if (s.current_state === 'YELLOW') duration = s.yellow_time;
                else if (s.current_state === 'RED') duration = s.red_time;

                // If Emergency, time is SOS
                const timeEl = document.getElementById(`time-${s.direction}`);
                if (timeEl) {
                    if (isEmergency) {
                        timeEl.innerText = 'SOS';
                        timeEl.style.color = '#ef4444';
                    } else {
                        const remaining = Math.max(0, Math.ceil(duration - elapsed));
                        timeEl.innerText = remaining + 's';
                        // Color code time
                        if (remaining <= 5) timeEl.style.color = '#ef4444'; // Red warning
                        else timeEl.style.color = stateColor;
                    }
                }
            } else {
                const timeEl = document.getElementById(`time-${s.direction}`);
                if (timeEl) timeEl.innerText = '--';
            }

            // 7. Update Border (Emergency Mode / Active State)
            if (isEmergency) {
                card.classList.add('emergency-mode');
                card.classList.remove('active-green', 'active-red', 'active-yellow');
            } else {
                card.classList.remove('emergency-mode');
                // Add active state class
                card.classList.remove('active-green', 'active-red', 'active-yellow');
                if (s.current_state === 'GREEN') card.classList.add('active-green');
                if (s.current_state === 'RED') card.classList.add('active-red');
                if (s.current_state === 'YELLOW') card.classList.add('active-yellow');
            }
        }

        // This is still needed for any separate visual logic if it exists
        updateVisualSignal(s);
    });
}

function updateVisualSignal(s) {
    const visualSignal = document.getElementById(`signal-${s.direction}`);
    if (visualSignal) {
        const redLight = visualSignal.querySelector('.light.red');
        const yellowLight = visualSignal.querySelector('.light.yellow');
        const greenLight = visualSignal.querySelector('.light.green');

        if (redLight) redLight.classList.remove('active');
        if (yellowLight) yellowLight.classList.remove('active');
        if (greenLight) greenLight.classList.remove('active');

        if (s.current_state === 'RED') {
            if (redLight) redLight.classList.add('active');
        } else if (s.current_state === 'YELLOW') {
            if (yellowLight) yellowLight.classList.add('active');
        } else if (s.current_state === 'GREEN') {
            if (greenLight) greenLight.classList.add('active');
        }
    }
}

// ============================================================
// SIMULATION
// ============================================================

function updateStatusUI(active) {
    const statusEl = document.getElementById('simStatus');
    if (statusEl) {
        statusEl.innerText = active ? 'Running...' : 'Stopped';
        statusEl.style.color = active ? 'var(--neon-green)' : 'var(--text-secondary)';
    }
}

function startSimulation() {
    console.log('▶ Starting Simulation');
    if (simulationActive) return;
    simulationActive = true;
    updateStatusUI(true);
    simulateTraffic();
}

function stopSimulation() {
    console.log('⏹ Stopping Simulation');
    simulationActive = false;
    updateStatusUI(false);
}

// ============================================================
// TRAFFIC QUEUE LOGIC
// ============================================================

// Local state to track actual vehicle queues (Arrivals - Departures)
let vehicleQueues = {
    N: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    S: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    E: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 },
    W: { two_wheeler: 0, four_wheeler: 0, heavy_vehicle: 0, emergency_vehicle: 0 }
};

async function simulateTraffic() {
    while (simulationActive) {
        // 1. Update Queues (Arrivals & Departures)
        for (const dir in signalData) {
            const signal = signalData[dir];
            const queue = vehicleQueues[dir];

            // --- ARRIVALS (Random Inflow) ---
            // Randomly add vehicles to the back of the queue
            if (Math.random() > 0.3) { // 70% chance of arrival per tick
                const rand = Math.random();
                if (rand < 0.6) queue.two_wheeler++;        // 60% Bike
                else if (rand < 0.9) queue.four_wheeler++;  // 30% Car
                else queue.heavy_vehicle++;                 // 10% Truck
            }

            // --- DEPARTURES (Outflow if Green) ---
            if (signal.current_state === 'GREEN') {
                // Flow Rate: How many can cross per second?
                // Let's say 2 vehicles per tick (1 tick = 1 sec usually)
                let flowCapacity = 2;

                // Prioritize Emergency -> Heavy -> Car -> Bike? Or FIFO?
                // Simplified: Emergency first, then random or simple decrement

                while (flowCapacity > 0) {
                    if (queue.emergency_vehicle > 0) {
                        queue.emergency_vehicle--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.emergency++;
                        flowCapacity--;
                    } else if (queue.heavy_vehicle > 0) {
                        queue.heavy_vehicle--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.truck++;
                        flowCapacity--; // Heavy takes 1 slot? Or more? Let's say 1 for simplicity of count
                    } else if (queue.four_wheeler > 0) {
                        queue.four_wheeler--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.car++;
                        flowCapacity--;
                    } else if (queue.two_wheeler > 0) {
                        queue.two_wheeler--;
                        vehicleExtra[dir].crossed++;
                        vehicleExtra[dir].passed_breakdown.bike++;
                        flowCapacity--;
                    } else {
                        break; // Queue empty
                    }
                }
            }

            // Sync Emergency Status manually if count > 0 (just to be safe, though Backend handles it)
            // But we rely on Backend to set 'is_emergency_active' flag via update response

            // --- UPDATE BACKEND ---
            // Calculate Delta Passed
            const currentCrossed = vehicleExtra[dir].crossed;
            const deltaPassed = currentCrossed - (vehicleExtra[dir].lastCrossed || 0);
            vehicleExtra[dir].lastCrossed = currentCrossed;

            // Send the CURRENT QUEUE SNAPSHOT + DELTA PASSED
            // Calculate breakdown deltas since last send?
            // Actually, we can just send the accumulated passed breakdown since last success?
            // To simplify: we send the current `passed_breakdown` accumulation and reset it?
            // Or send delta. Let's send accumulated delta since last send.
            // But `vehicleExtra` state persists. 
            // Better: Reset `passed_breakdown` after successful send? No, we might fail.
            // Let's reset it here assume it will send.

            const passed = vehicleExtra[dir].passed_breakdown;
            const payload = {
                two_wheeler: queue.two_wheeler,
                four_wheeler: queue.four_wheeler,
                heavy_vehicle: queue.heavy_vehicle,
                emergency_vehicle: queue.emergency_vehicle,
                vehicles_passed: deltaPassed,

                // Detailed Passed
                passed_two_wheeler: passed.bike,
                passed_four_wheeler: passed.car,
                passed_heavy_vehicle: passed.truck,
                passed_emergency_vehicle: passed.emergency
            };

            // Allow update
            await updateVehicleCount(dir, payload);

            // Reset local passed counters after sending
            vehicleExtra[dir].passed_breakdown = { bike: 0, car: 0, truck: 0, emergency: 0 };
        }

        // 2. Cycle Signals (Backend decides state changes)
        await cycleSignals();

        // 3. Wait for next tick
        await new Promise(r => setTimeout(r, updateInterval));
    }
}

// ============================================================
// LOGS
// ============================================================

function addLog(msg) {
    console.log(msg);
}

// ============================================================
// DETAILS MODAL LOGIC
// ============================================================

let detailsChartInstance = null;

async function showDirectionDetails(direction) {
    const modal = document.getElementById('detailsModal');
    const title = document.getElementById('modalTitle');

    // Reset Data
    title.innerText = `Direction: ${signalData[direction].direction} Loading...`;
    modal.style.display = 'flex';

    try {
        // Fetch Summary
        const summaryRes = await fetch(`/api/analytics/direction/${direction}/summary?format=json`);
        const summary = await summaryRes.json();

        // Fetch Charts
        const chartRes = await fetch(`/api/analytics/direction/${direction}/charts?format=json`);
        const chartData = await chartRes.json();

        // Populate Summary
        title.innerText = `Direction: ${summary.direction} Details`;
        // Use Current Queue Total to match the Breakdown list below
        document.getElementById('modalTotalVehicles').innerText = summary.current_vehicles;
        document.getElementById('modalPeakDensity').innerText = summary.max_density_score.toFixed(1);
        document.getElementById('modalGreenTime').innerText = summary.total_green_time + 's';

        // Populate List
        const list = document.getElementById('modalBreakdownList');
        list.innerHTML = `
            <li><span><i class="fa-solid fa-motorcycle"></i> Two Wheelers</span> <strong>${summary.vehicle_breakdown.two_wheeler}</strong></li>
            <li><span><i class="fa-solid fa-car"></i> Cars</span> <strong>${summary.vehicle_breakdown.four_wheeler}</strong></li>
            <li><span><i class="fa-solid fa-truck"></i> Heavy Vehicles</span> <strong>${summary.vehicle_breakdown.heavy_vehicle}</strong></li>
            <li><span><i class="fa-solid fa-truck-medical text-danger"></i> Emergency</span> <strong>${summary.vehicle_breakdown.emergency_vehicle}</strong></li>
        `;

        // Render Chart
        renderDetailsChart(chartData.flow_labels, chartData.flow_data);

    } catch (e) {
        console.error(e);
        title.innerText = 'Error Loading Data';
    }
}

function renderDetailsChart(labels, data) {
    const canvas = document.getElementById('detailsChart');
    const ctx = canvas.getContext('2d');

    if (detailsChartInstance) {
        detailsChartInstance.destroy();
    }

    // Create Gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)'); // Blue top
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)'); // Transparent bottom

    detailsChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Traffic Flow',
                data: data,
                borderColor: '#60a5fa', // Lighter Blue
                backgroundColor: gradient,
                borderWidth: 3,
                pointBackgroundColor: '#ffffff',
                pointBorderColor: '#60a5fa',
                pointHoverBackgroundColor: '#60a5fa',
                pointHoverBorderColor: '#ffffff',
                pointRadius: 4,
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
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        borderDash: [5, 5]
                    },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: 'Inter' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        label: function (context) {
                            return context.parsed.y + ' Vehicle(s)';
                        }
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false,
            }
        }
    });
}

function closeDetailsModal() {
    document.getElementById('detailsModal').style.display = 'none';
}

// ============================================================
// CORE LOGIC (Restored)
// ============================================================

async function initializeDashboard() {
    console.log('Initializing Dashboard...');
    const signals = await fetchSignals();
    if (signals && signals.length > 0) {
        updateAllControls(signals);
        // Also update the global stats
        fetchGlobalStats();
    } else {
        console.error('No signals loaded.');
    }
}

async function fetchGlobalStats() {
    try {
        // Parallel fetch for stats
        const [globalRes, effRes] = await Promise.all([
            fetch('/api/signals/global_stats/'),
            fetch('/api/signals/efficiency_stats/')
        ]);

        if (globalRes.ok) {
            const gData = await globalRes.json();
            const crossedEl = document.getElementById('crossedTotal');
            if (crossedEl) crossedEl.innerText = gData.total_passed_today;
        }

        if (effRes.ok) {
            const eData = await effRes.json();
            // We mainly have IDs: totalVehicles, greenSignals, crossedTotal
            // We can check if we can populate others.
            // HTML Static: <h2 id="totalVehicles">0</h2>
            // We don't have a direct API for "totalVehicles" in system (QUEUE), 
            // but we can sum it up from signals in `updateAllControls`.
        }
    } catch (e) {
        console.warn("Stats fetch failed:", e);
    }
}

async function cycleSignals() {
    try {
        const response = await fetch('/api/signals/cycle_signals/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        const data = await response.json();
        if (data && Array.isArray(data)) {
            updateAllControls(data);
        }
    } catch (e) {
        console.error("Cycle signals failed:", e);
    }
}

function addVehicle(direction, type) {
    const map = { 'bike': 'two_wheeler', 'car': 'four_wheeler', 'truck': 'heavy_vehicle' };
    const key = map[type];
    if (vehicleQueues[direction] && key) {
        vehicleQueues[direction][key]++;
        // Visual feedback
        const btn = document.querySelector(`#control-${direction} .btn-add-vehicle[title*="${type}"]`); // approximate
        if (btn) {
            btn.style.transform = "scale(0.95)";
            setTimeout(() => btn.style.transform = "", 100);
        }
    }
}

async function triggerEmergency(direction) {
    const signal = signalData[direction];
    if (!signal) return;

    const newState = !signal.is_emergency_active;
    try {
        const response = await fetch(`/api/signals/${signal.id}/toggle_sos/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ active: newState })
        });
        const updated = await response.json();
        signalData[direction] = updated;
        updateAllControls([updated]);
    } catch (e) {
        alert("SOS Toggle Failed");
    }
}

// Make globally available
window.showDirectionDetails = showDirectionDetails;
window.closeDetailsModal = closeDetailsModal;
window.addVehicle = addVehicle;
window.triggerEmergency = triggerEmergency;

// ============================================================
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeDashboard();
    fetchGlobalStats(); // Fetch persistent total

    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');

    if (startBtn) startBtn.addEventListener('click', startSimulation);
    if (stopBtn) stopBtn.addEventListener('click', stopSimulation);

    // Reset handled inline or add listener if id exists
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) resetBtn.addEventListener('click', resetSystem);
});

async function resetSystem() {
    if (!confirm("⚠️ DANGER: This will delete ALL history and reset signals. Continue?")) return;

    try {
        const res = await fetch('/api/signals/reset_system/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        if (res.ok) {
            alert("System Reset Complete. Reloading...");
            window.location.reload();
        } else {
            alert("Reset Failed.");
        }
    } catch (e) {
        console.error(e);
        alert("Reset Error.");
    }
}
