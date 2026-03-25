// ============================================================
// HISTORY & LOGIC
// ============================================================

let currentHistoryPage = 1;
let currentDirectionFilter = null;
let totalPages = 1;

async function loadHistory(page = 1, direction = null, tabElement = null) {
    if (tabElement) {
        // Handle Tab Styling
        document.querySelectorAll('#view-history .dir-tab').forEach(t => t.classList.remove('active'));
        tabElement.classList.add('active');
    }

    currentHistoryPage = page;
    currentDirectionFilter = direction;

    let url = `/api/signals/history/?page=${page}&page_size=15`;
    if (direction) {
        url += `&direction=${direction}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        renderHistoryTable(data.results);
        updatePagination(data);
    } catch (e) {
        console.error("Failed to load history", e);
    }
}

function renderHistoryTable(logs) {
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '';

    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-secondary);">No records found.</td></tr>';
        return;
    }

    logs.forEach(log => {
        const tr = document.createElement('tr');

        let statusBadge = `<span style="color:var(--neon-green)">NORMAL</span>`;
        if (log.is_emergency) statusBadge = `<span style="color:var(--neon-red); font-weight:bold;">SOS / EMERGENCY</span>`;
        else if (log.vehicle_count > 30) statusBadge = `<span style="color:var(--neon-yellow)">HEAVY</span>`;

        tr.innerHTML = `
            <td style="font-family:var(--font-mono); color:var(--accent-primary);">${log.timestamp}</td>
            <td style="font-weight:bold;">${log.direction === 'N' ? 'NORTH' : (log.direction === 'S' ? 'SOUTH' : (log.direction === 'E' ? 'EAST' : 'WEST'))}</td>
            <td>${log.vehicle_count}</td>
            <td>${log.density}</td>
            <td><span class="signal-badge ${log.signal_state}">${log.signal_state}</span></td>
            <td>${statusBadge}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updatePagination(data) {
    totalPages = data.total_pages;
    document.getElementById('pageInfo').innerText = `Page ${data.current_page} of ${data.total_pages}`;

    document.getElementById('prevPageBtn').disabled = !data.previous && data.current_page === 1; // logical check: no prev if page 1
    if (data.current_page > 1) document.getElementById('prevPageBtn').disabled = false;
    else document.getElementById('prevPageBtn').disabled = true;

    document.getElementById('nextPageBtn').disabled = !data.has_next;
}

function changeHistoryPage(delta) {
    const newPage = currentHistoryPage + delta;
    if (newPage > 0 && newPage <= totalPages) {
        loadHistory(newPage, currentDirectionFilter);
    }
}
