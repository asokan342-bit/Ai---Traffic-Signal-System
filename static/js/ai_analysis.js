/**
 * AI Analysis — Upload & Live Mode Controller
 * Handles video upload detection and live camera processing.
 * Live Mode uses browser getUserMedia API for camera display.
 */

// =====================================================
// STATE
// =====================================================
let currentAiMode = 'upload'; // 'upload' or 'live'
let liveStreamActive = false;
let livePollingTimer = null;
let cameraConnected = false;
let cameraStream = null;
const API_BASE = '/api';

// =====================================================
// MODE SWITCHING
// =====================================================
function switchAiMode(mode) {
    currentAiMode = mode;
    document.querySelectorAll('.ai-mode-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`[data-ai-mode="${mode}"]`).classList.add('active');

    document.getElementById('aiUploadPanel').style.display = mode === 'upload' ? 'block' : 'none';
    document.getElementById('aiLivePanel').style.display = mode === 'live' ? 'block' : 'none';

    if (mode === 'live') {
        stopLiveStream(); // Reset before starting
    } else {
        stopLiveStream();
    }
}

// =====================================================
// UPLOAD MODE
// =====================================================
function initUploadZone() {
    const zone = document.getElementById('aiUploadZone');
    const fileInput = document.getElementById('aiVideoInput');
    if (!zone || !fileInput) return;

    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleVideoUpload(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleVideoUpload(e.target.files[0]);
    });
}

function handleVideoUpload(file) {
    const validTypes = ['video/mp4', 'video/avi', 'video/x-msvideo', 'video/quicktime', 'video/webm', 'video/x-matroska'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|avi|mov|webm|mkv)$/i)) {
        showAiNotification('Invalid file type. Please upload MP4, AVI, MOV, or WebM.', 'error');
        return;
    }

    // Show progress
    const progressContainer = document.getElementById('aiProgressContainer');
    const progressBar = document.getElementById('aiProgressBar');
    const progressText = document.getElementById('aiProgressText');
    const progressPercent = document.getElementById('aiProgressPercent');

    progressContainer.classList.add('active');
    document.getElementById('aiUploadResults').classList.remove('active');

    // Animate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 8;
        if (progress > 92) progress = 92;
        progressBar.style.width = progress + '%';
        progressPercent.textContent = Math.round(progress) + '%';
        progressText.textContent = progress < 30 ? 'Uploading video...'
            : progress < 60 ? 'Extracting frames...'
                : progress < 85 ? 'Running YOLO detection...'
                    : 'Calculating signal timings...';
    }, 300);

    // Upload via fetch
    const formData = new FormData();
    formData.append('video', file);

    fetch(`${API_BASE}/ai-analysis/upload/`, {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCSRFToken() },
    })
        .then(res => res.json())
        .then(data => {
            clearInterval(progressInterval);
            progressBar.style.width = '100%';
            progressPercent.textContent = '100%';
            progressText.textContent = 'Analysis complete!';

            setTimeout(() => {
                progressContainer.classList.remove('active');
                displayUploadResults(data);
            }, 500);
        })
        .catch(err => {
            clearInterval(progressInterval);
            progressContainer.classList.remove('active');
            showAiNotification('Analysis failed: ' + err.message, 'error');
        });
}

function displayUploadResults(data) {
    const resultsContainer = document.getElementById('aiUploadResults');
    resultsContainer.classList.add('active');

    // Overall stats
    document.getElementById('aiTotalVehicles').textContent = data.total_vehicles || 0;
    document.getElementById('aiTotalFrames').textContent = data.total_frames || 0;
    document.getElementById('aiProcessedFrames').textContent = data.processed_frames || 0;
    document.getElementById('aiAvgPerFrame').textContent = data.avg_per_frame || 0;

    // Overall density
    const overallDensity = document.getElementById('aiOverallDensity');
    const density = data.density || 'Low Traffic';
    overallDensity.textContent = density;
    overallDensity.className = 'ai-overall-density ' + getDensityClass(density);

    // Vehicle breakdown
    if (data.counts) {
        document.getElementById('aiCarCount').textContent = data.counts.car || 0;
        document.getElementById('aiTruckCount').textContent = data.counts.truck || 0;
        document.getElementById('aiBusCount').textContent = data.counts.bus || 0;
        document.getElementById('aiMotoCount').textContent = data.counts.motorcycle || 0;
        document.getElementById('aiBicycleCount').textContent = data.counts.bicycle || 0;
    }

    // Lane cards
    renderLaneCards('aiLaneGrid', data.lane_data);

    // Annotated frame
    const framePreview = document.getElementById('aiFramePreview');
    if (data.annotated_frame) {
        framePreview.innerHTML = `
            <div class="ai-frame-overlay">
                <i class="fa-solid fa-eye"></i> YOLO Detection Output
            </div>
            <img src="data:image/jpeg;base64,${data.annotated_frame}" alt="Annotated Frame">
        `;
        framePreview.style.display = 'block';
    } else {
        framePreview.style.display = 'none';
    }

    // Load history
    loadAnalysisHistory();
}

// =====================================================
// LANE CARD RENDERING
// =====================================================
function renderLaneCards(containerId, laneData) {
    const container = document.getElementById(containerId);
    if (!container || !laneData) return;

    const directionNames = { N: 'North', S: 'South', E: 'East', W: 'West' };
    const directionIcons = { N: 'fa-arrow-up', S: 'fa-arrow-down', E: 'fa-arrow-right', W: 'fa-arrow-left' };

    container.innerHTML = '';
    for (const [lane, info] of Object.entries(laneData)) {
        const totalTime = (info.green || 10) + (info.yellow || 5) + (info.red || 10);
        const greenW = ((info.green || 10) / totalTime * 100).toFixed(1);
        const yellowW = ((info.yellow || 5) / totalTime * 100).toFixed(1);
        const redW = ((info.red || 10) / totalTime * 100).toFixed(1);

        const densityClass = getDensityClass(info.density || 'Low Traffic');
        const activeLight = info.density === 'High Traffic' ? 'green' : info.density === 'Medium Traffic' ? 'yellow' : 'red';

        const card = document.createElement('div');
        card.className = `ai-lane-card lane-${lane}`;
        card.innerHTML = `
            <div class="ai-lane-direction">
                <i class="fa-solid ${directionIcons[lane] || 'fa-road'}"></i> ${directionNames[lane] || lane}
            </div>
            <div class="ai-lane-count">${info.vehicle_count || 0}</div>
            <div class="ai-lane-label">Vehicles</div>
            <div class="ai-density-badge ${densityClass}">
                <i class="fa-solid fa-signal"></i> ${info.density || 'Low Traffic'}
            </div>
            <div class="ai-traffic-light">
                <div class="ai-light-dot red ${activeLight === 'red' ? 'active' : ''}"></div>
                <div class="ai-light-dot yellow ${activeLight === 'yellow' ? 'active' : ''}"></div>
                <div class="ai-light-dot green ${activeLight === 'green' ? 'active' : ''}"></div>
            </div>
            <div class="ai-signal-timing">
                <div class="timing-green" style="width:${greenW}%"></div>
                <div class="timing-yellow" style="width:${yellowW}%"></div>
                <div class="timing-red" style="width:${redW}%"></div>
            </div>
            <div class="ai-timing-labels">
                <span style="color:#22c55e">G: ${info.green || 10}s</span>
                <span style="color:#eab308">Y: ${info.yellow || 5}s</span>
                <span style="color:#ef4444">R: ${info.red || 10}s</span>
            </div>
        `;
        container.appendChild(card);
    }
}

function getDensityClass(density) {
    if (!density) return 'density-low';
    const d = density.toLowerCase();
    if (d.includes('high')) return 'density-high';
    if (d.includes('medium')) return 'density-medium';
    return 'density-low';
}

// =====================================================
// LIVE MODE — Browser Camera API (getUserMedia)
// =====================================================

function updateCameraStatusUI(status, title, subtitle) {
    const indicator = document.getElementById('cameraStatusIndicator');
    const icon = document.getElementById('cameraStatusIcon');
    const titleEl = document.getElementById('cameraStatusTitle');
    const subtitleEl = document.getElementById('cameraStatusSubtitle');
    const placeholder = document.getElementById('aiLivePlaceholder');
    const startBtn = document.getElementById('aiLiveStartBtn');

    if (!indicator) return;

    indicator.className = 'camera-status-indicator ' + status;

    if (status === 'connected') {
        icon.className = 'fa-solid fa-video';
        cameraConnected = true;
        if (startBtn) startBtn.disabled = false;
        if (placeholder) {
            const mainText = placeholder.querySelector('.placeholder-main-text');
            const subText = placeholder.querySelector('.placeholder-sub-text');
            const iconEl = placeholder.querySelector('i');
            if (mainText) mainText.textContent = 'Camera Ready';
            if (subText) subText.textContent = 'Click Start Stream to begin live traffic detection with YOLO AI';
            if (iconEl) iconEl.className = 'fa-solid fa-video';
        }
    } else if (status === 'disconnected') {
        icon.className = 'fa-solid fa-video-slash';
        cameraConnected = false;
        if (startBtn) startBtn.disabled = true;
        if (placeholder) {
            const mainText = placeholder.querySelector('.placeholder-main-text');
            const subText = placeholder.querySelector('.placeholder-sub-text');
            const iconEl = placeholder.querySelector('i');
            if (mainText) mainText.textContent = 'Camera Not Connected Yet';
            if (subText) subText.textContent = 'Connect a camera and click Check Camera to verify, then start the live stream';
            if (iconEl) iconEl.className = 'fa-solid fa-video-slash';
        }
    } else if (status === 'checking') {
        icon.className = 'fa-solid fa-spinner';
    }

    titleEl.textContent = title;
    subtitleEl.textContent = subtitle;
}

async function checkCameraStatus() {
    updateCameraStatusUI('checking', 'Checking Camera...', 'Detecting connected camera devices...');

    try {
        // Use browser API to check camera availability
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        // Camera works — stop it immediately (this is just a check)
        stream.getTracks().forEach(t => t.stop());
        updateCameraStatusUI('connected', 'Camera Connected', 'Camera device detected and ready for live streaming');
        showAiNotification('Camera detected! You can now start the live stream.', 'success');
    } catch (err) {
        let msg = 'No camera device detected. Please connect a webcam and try again.';
        if (err.name === 'NotAllowedError') {
            msg = 'Camera access denied. Please allow camera permission in your browser and try again.';
        } else if (err.name === 'NotFoundError') {
            msg = 'No camera device found. Please connect a webcam or IP camera.';
        } else if (err.name === 'NotReadableError') {
            msg = 'Camera is in use by another application. Please close other apps using the camera.';
        }
        updateCameraStatusUI('disconnected', 'Camera Not Connected', msg);
        showAiNotification(msg, 'error');
    }
}

async function startLiveStream() {
    if (!cameraConnected) {
        showAiNotification('Please connect a camera first. Click "Check Camera" to verify.', 'error');
        return;
    }

    try {
        // Open camera via browser API
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'environment' }
        });

        const video = document.getElementById('aiLiveVideo');
        const placeholder = document.getElementById('aiLivePlaceholder');
        const badge = document.getElementById('aiLiveBadge');

        video.srcObject = cameraStream;
        video.style.display = 'block';
        if (placeholder) placeholder.style.display = 'none';
        if (badge) badge.style.display = 'flex';

        liveStreamActive = true;

        document.getElementById('aiLiveStartBtn').disabled = true;
        document.getElementById('aiLiveStopBtn').disabled = false;

        // Start periodic frame analysis — send captured frames to backend for YOLO
        sendFrameForAnalysis();
        livePollingTimer = setInterval(sendFrameForAnalysis, 3000);

        updateCameraStatusUI('connected', 'Camera Streaming', 'Live feed active — analyzing traffic with AI');
    } catch (err) {
        let msg = 'Failed to start camera stream.';
        if (err.name === 'NotAllowedError') msg = 'Camera permission denied by browser.';
        else if (err.name === 'NotFoundError') msg = 'Camera disconnected.';
        else if (err.name === 'NotReadableError') msg = 'Camera in use by another application.';

        updateCameraStatusUI('disconnected', 'Camera Error', msg);
        showAiNotification(msg, 'error');
        cameraConnected = false;
    }
}

function stopLiveStream() {
    liveStreamActive = false;

    // Stop browser camera stream
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    const video = document.getElementById('aiLiveVideo');
    const placeholder = document.getElementById('aiLivePlaceholder');
    const badge = document.getElementById('aiLiveBadge');

    if (video) {
        video.srcObject = null;
        video.style.display = 'none';
    }
    if (placeholder) placeholder.style.display = 'block';
    if (badge) badge.style.display = 'none';

    if (livePollingTimer) {
        clearInterval(livePollingTimer);
        livePollingTimer = null;
    }

    const startBtn = document.getElementById('aiLiveStartBtn');
    const stopBtn = document.getElementById('aiLiveStopBtn');
    if (startBtn) startBtn.disabled = !cameraConnected;
    if (stopBtn) stopBtn.disabled = true;

    if (cameraConnected) {
        updateCameraStatusUI('connected', 'Camera Connected', 'Stream stopped. Click Start Stream to resume.');
    }
}

function sendFrameForAnalysis() {
    if (!liveStreamActive) return;

    const video = document.getElementById('aiLiveVideo');
    const canvas = document.getElementById('aiLiveCanvas');
    if (!video || !canvas || video.readyState < 2) return;

    // Capture current frame from video element
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to blob and send to backend for YOLO analysis
    canvas.toBlob(function (blob) {
        if (!blob || !liveStreamActive) return;

        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');

        fetch(`${API_BASE}/ai-analysis/analyze-frame/`, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': getCSRFToken() },
        })
            .then(res => res.json())
            .then(data => {
                if (!liveStreamActive) return;

                // Update live stats
                document.getElementById('aiLiveTotalVehicles').textContent = data.total_vehicles || 0;

                const liveOverallDensity = document.getElementById('aiLiveOverallDensity');
                const density = data.density || 'Low Traffic';
                liveOverallDensity.textContent = density;
                liveOverallDensity.className = 'ai-overall-density ' + getDensityClass(density);

                // Update vehicle counts
                if (data.counts) {
                    document.getElementById('aiLiveCarCount').textContent = data.counts.car || 0;
                    document.getElementById('aiLiveTruckCount').textContent = data.counts.truck || 0;
                    document.getElementById('aiLiveBusCount').textContent = data.counts.bus || 0;
                    document.getElementById('aiLiveMotoCount').textContent = data.counts.motorcycle || 0;
                    document.getElementById('aiLiveBicycleCount').textContent = data.counts.bicycle || 0;
                }

                // Update lane cards
                renderLaneCards('aiLiveLaneGrid', data.lane_data);

                // Show results
                document.getElementById('aiLiveResults').classList.add('active');
            })
            .catch(err => console.warn('Frame analysis error:', err));
    }, 'image/jpeg', 0.7);
}

// =====================================================
// HISTORY
// =====================================================
function loadAnalysisHistory() {
    fetch(`${API_BASE}/ai-analysis/history/`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById('aiHistoryBody');
            if (!tbody) return;

            if (!data.results || data.results.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:rgba(255,255,255,0.3); padding:20px;">No analysis records yet.</td></tr>';
                return;
            }

            tbody.innerHTML = data.results.map(r => `
                <tr>
                    <td>${r.created_at}</td>
                    <td>
                        <span style="padding:3px 10px; border-radius:6px; font-size:0.75rem; font-weight:600;
                            background:${r.mode === 'UPLOAD' ? 'rgba(99,102,241,0.2)' : 'rgba(239,68,68,0.2)'};
                            color:${r.mode === 'UPLOAD' ? '#818cf8' : '#f87171'};">
                            ${r.mode === 'UPLOAD' ? '<i class="fa-solid fa-upload"></i>' : '<i class="fa-solid fa-video"></i>'} ${r.mode}
                        </span>
                    </td>
                    <td style="font-weight:700; color:#22d3ee;">${r.total_vehicles}</td>
                    <td>
                        <span class="ai-density-badge ${getDensityClass(r.density_label)}">
                            ${r.density_label}
                        </span>
                    </td>
                    <td>${r.total_frames}</td>
                </tr>
            `).join('');
        })
        .catch(err => console.warn('History error:', err));
}

// =====================================================
// NOTIFICATIONS
// =====================================================
function showAiNotification(message, type) {
    // Reuse existing notification system if available
    if (typeof showNotification === 'function') {
        showNotification(type === 'error' ? 'Error' : 'Info', message);
    } else {
        alert(message);
    }
}

// =====================================================
// CSRF TOKEN
// =====================================================
function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let c of cookies) {
        c = c.trim();
        if (c.startsWith('csrftoken=')) {
            return c.substring('csrftoken='.length);
        }
    }
    // Try meta tag
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.getAttribute('content');
    return '';
}

// =====================================================
// INIT
// =====================================================
function initAiAnalysis() {
    initUploadZone();
    loadAnalysisHistory();
}

// Auto-init when view becomes visible
document.addEventListener('DOMContentLoaded', () => {
    // Will be initialized when view is switched to
});
