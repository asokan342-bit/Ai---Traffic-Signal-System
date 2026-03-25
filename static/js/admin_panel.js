/**
 * Admin Panel Module
 * Handles action log display, filtering, and admin role information.
 */

async function initAdminView() {
    loadAdminLogs();
    loadAdminStats();
}

async function loadAdminStats() {
    try {
        // Get total admin logs
        const logsRes = await fetch('/api/admin-logs/');
        const logsData = await logsRes.json();
        const logs = logsData.results || logsData;

        document.getElementById('adminTotalActions').textContent = Array.isArray(logs) ? logs.length : 0;

        // Count overrides
        const overrides = Array.isArray(logs) ? logs.filter(l => l.action_type === 'MANUAL_OVERRIDE').length : 0;
        document.getElementById('adminOverrides').textContent = overrides;

        // Get junction count
        const jnRes = await fetch('/api/junctions/');
        const jnData = await jnRes.json();
        const junctions = jnData.results || jnData;
        document.getElementById('adminJunctions').textContent = Array.isArray(junctions) ? junctions.length : 0;

    } catch (err) {
        console.error('Admin stats error:', err);
    }
}

async function loadAdminLogs() {
    try {
        const filter = document.getElementById('adminLogFilter');
        let url = '/api/admin-logs/';
        if (filter && filter.value) {
            url += `?action_type=${filter.value}`;
        }

        const res = await fetch(url);
        const data = await res.json();
        const logs = data.results || data;

        const tbody = document.getElementById('adminLogBody');
        if (!tbody) return;

        tbody.innerHTML = '';

        if (!Array.isArray(logs) || logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-secondary);">No action logs recorded.</td></tr>';
            return;
        }

        logs.forEach(log => {
            const row = document.createElement('tr');
            const actionBadge = getActionBadge(log.action_type);
            row.innerHTML = `
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${log.username || 'System'}</td>
                <td>${actionBadge}</td>
                <td>${log.junction_name || '--'}</td>
                <td>${log.description || '--'}</td>
            `;
            tbody.appendChild(row);
        });
    } catch (err) {
        console.error('Admin logs error:', err);
    }
}

function getActionBadge(actionType) {
    const badges = {
        'MANUAL_OVERRIDE': '<span class="action-badge action-override">Manual Override</span>',
        'TIMING_CONFIG': '<span class="action-badge action-timing">Timing Config</span>',
        'EMERGENCY_TOGGLE': '<span class="action-badge action-emergency">Emergency Toggle</span>',
        'SYSTEM_RESET': '<span class="action-badge action-reset">System Reset</span>',
        'JUNCTION_CONFIG': '<span class="action-badge action-junction">Junction Config</span>',
        'OTHER': '<span class="action-badge action-other">Other</span>',
    };
    return badges[actionType] || `<span class="action-badge">${actionType}</span>`;
}
