// ─────────────── State ───────────────
let currentHash = null;
let html5QrCode = null;

// ─────────────── View Management ───────────────
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

// ─────────────── Toast Notifications ───────────────
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 2600);
}

// ─────────────── QR Scanner ───────────────
function initScanner() {
    if (html5QrCode) {
        try { html5QrCode.clear(); } catch (_) {}
    }

    html5QrCode = new Html5Qrcode("qr-reader");

    html5QrCode.start(
        { facingMode: "environment" },
        {
            fps: 10,
            qrbox: { width: 220, height: 220 },
            aspectRatio: 1.0,
        },
        onScanSuccess,
        (_errorMessage) => { /* silence scan errors */ }
    ).catch(err => {
        console.warn("Camera error:", err);
        // Fallback: show a manual input
        document.getElementById('qr-reader').innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding:20px;gap:12px;">
                <p style="color:var(--text-secondary);text-align:center;">Camera unavailable.<br>Enter QR hash manually:</p>
                <input type="text" id="manual-hash-input" placeholder="Paste QR hash" 
                       style="padding:14px;width:100%;font-size:1rem;border-radius:10px;border:1px solid var(--border-subtle);background:rgba(255,255,255,0.05);color:var(--text-primary);text-align:center;font-family:monospace;">
                <button onclick="manualLookup()" 
                        style="padding:12px 28px;background:var(--accent-purple);color:#fff;border:none;border-radius:10px;font-size:0.95rem;font-weight:600;cursor:pointer;">
                    Look Up Team
                </button>
            </div>
        `;
    });
}

function manualLookup() {
    const hash = document.getElementById('manual-hash-input').value.trim();
    if (hash) onScanSuccess(hash);
}

async function onScanSuccess(decodedText) {
    // Stop scanner immediately
    if (html5QrCode) {
        try { await html5QrCode.stop(); } catch (_) {}
    }

    const hash = decodedText.trim();
    currentHash = hash;

    // Fetch team data
    try {
        const res = await fetch(`/team/${hash}`);
        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || 'Team not found', 'error');
            resetToScanner();
            return;
        }

        const team = await res.json();
        populateScoringView(team, hash);
        showView('scoring-view');
    } catch (e) {
        showToast('Network error — check server', 'error');
        resetToScanner();
    }
}

// ─────────────── Populate Scoring View ───────────────
function populateScoringView(team, hash) {
    document.getElementById('team-name').textContent = team.team_name;
    document.getElementById('team-hash').textContent = hash;
    document.getElementById('teammate-wallet').textContent = team.teammate_wallet;
    document.getElementById('traitor-wallet').textContent = team.traitor_wallet;

    const membersContainer = document.getElementById('members-container');
    membersContainer.innerHTML = '';
    team.members.forEach(m => {
        const chip = document.createElement('span');
        chip.className = 'member-chip';
        chip.innerHTML = `<span class="band-dot" style="background:${sanitizeColor(m.band_color)}"></span> ${escapeHtml(m.name)}`;
        membersContainer.appendChild(chip);
    });

    // Reset inputs
    document.getElementById('max-points').value = 100;
    document.getElementById('stall-id').value = '';
    setButtonsEnabled(true);
}

// ─────────────── Submit Score ───────────────
async function submitScore(outcome) {
    const maxPoints = parseInt(document.getElementById('max-points').value);
    const stallId = document.getElementById('stall-id').value.trim() || 'unknown';

    if (!maxPoints || maxPoints < 1) {
        showToast('Enter valid max points', 'error');
        return;
    }

    if (!currentHash) {
        showToast('No team selected', 'error');
        return;
    }

    setButtonsEnabled(false);

    try {
        const res = await fetch('/score_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                qr_code_hash: currentHash,
                stall_id: stallId,
                max_points: maxPoints,
                outcome: outcome,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            showToast(err.detail || 'Scoring failed', 'error');
            setButtonsEnabled(true);
            return;
        }

        const data = await res.json();
        showToast(data.message, 'success');

        // Update wallet display briefly
        document.getElementById('teammate-wallet').textContent = data.teammate_wallet;
        document.getElementById('traitor-wallet').textContent = data.traitor_wallet;

        // Reset to scanner after delay
        setTimeout(() => resetToScanner(), 1800);
    } catch (e) {
        showToast('Network error', 'error');
        setButtonsEnabled(true);
    }
}

function setButtonsEnabled(enabled) {
    document.getElementById('btn-team-won').disabled = !enabled;
    document.getElementById('btn-traitor-won').disabled = !enabled;
}

// ─────────────── Reset to Scanner ───────────────
function resetToScanner() {
    currentHash = null;
    showView('scanner-view');
    initScanner();
}

// ─────────────── Utilities ───────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function sanitizeColor(color) {
    // Only allow safe CSS color values
    const safe = color.replace(/[^a-zA-Z0-9#(),.\s%]/g, '');
    return safe || '#888';
}

// ─────────────── Init ───────────────
document.addEventListener('DOMContentLoaded', () => {
    initScanner();
});
