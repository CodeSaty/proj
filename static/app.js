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
            <div class="flex flex-col items-center justify-center w-full h-full p-4 gap-3 bg-surface-container-lowest z-50 relative pointer-events-auto">
                <p class="text-error font-label-hud tracking-widest text-center text-[10px] animate-pulse">CAMERA OFFLINE<br>MANUAL OVERRIDE</p>
                <input type="text" id="manual-hash-input" placeholder="ENTER HASH..." 
                       class="w-full bg-surface-container border border-error/50 text-error font-code-terminal text-center py-2 focus:border-error focus:ring-0 outline-none">
                <button onclick="manualLookup()" 
                        class="w-full bg-error/10 border border-error text-error font-label-hud tracking-widest py-2 hover:bg-error hover:text-surface-container-lowest transition-colors shadow-[0_0_10px_rgba(255,180,171,0.2)]">
                    EXECUTE LOOKUP
                </button>
            </div>
        `;
    });
}

function manualLookup() {
    const hash = document.getElementById('manual-hash-input').value.trim();
    if (hash) onScanSuccess(hash);
}

function manualLookupMain() {
    const hash = document.getElementById('manual-hash-input-main').value.trim();
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
        // is_traitor is now hidden by backend, so it will always appear as an operative
        const role = { text: 'OPERATIVE', colorClass: 'text-primary', bgClass: 'bg-surface-container-lowest/80', borderClass: 'border-outline-variant/70', dotColor: '#e5b5ff', tagBg: 'bg-primary/10' };

        const card = document.createElement('div');
        card.className = `border ${role.borderClass} ${role.bgClass} p-2 flex flex-col justify-between`;
        
        card.innerHTML = `
            <div class="flex items-center justify-between mb-1">
                <span class="font-code-terminal text-on-surface font-semibold text-xs truncate">${escapeHtml(m.name)}</span>
            </div>
            <div class="mb-2">
                <span class="text-[9px] font-label-hud ${role.colorClass} ${role.tagBg} px-1 py-0.5 border border-current tracking-wider font-bold">
                    ${role.text}
                </span>
            </div>
            <div class="mt-1 flex flex-col gap-1">
                <span class="text-[10px] text-outline font-code-terminal">Roll: <span class="text-secondary">${escapeHtml(m.roll_number)}</span></span>
                <span class="text-[10px] text-outline font-code-terminal">Branch: <span class="text-secondary">${escapeHtml(m.branch)}</span></span>
                <span class="text-[10px] text-outline font-code-terminal">Course: <span class="text-secondary">${escapeHtml(m.course)} (${escapeHtml(m.study_year)})</span></span>
            </div>
        `;
        membersContainer.appendChild(card);
    });

    // Reset inputs
    document.getElementById('max-points').value = 100;
    document.getElementById('stall-id').value = '';
    setButtonsEnabled(true);
}

// ─────────────── Adjust Points ───────────────
function adjustPoints(delta) {
    const input = document.getElementById('max-points');
    let val = parseInt(input.value) || 100;
    val += delta;
    if (val < 10) val = 10;
    if (val > 10000) val = 10000;
    input.value = val;
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
