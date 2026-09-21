// register.js
document.addEventListener("DOMContentLoaded", () => {
    // The main execute button is the one at the bottom calling triggerSubmission(this)
    // We will override its behavior
    const registerBtn = document.querySelector("button.pulse-glow"); 
    const teamNameInput = document.getElementById("syndicate-alias");

    if (registerBtn) {
        // Remove the onclick attribute so we can handle it cleanly
        registerBtn.removeAttribute("onclick");
        
        registerBtn.addEventListener("click", async () => {
            const teamName = teamNameInput.value.trim();
            
            if (!teamName) {
                alert("ALERT: SYNDICATE ALIAS CALLSIGN IS MANDATORY.");
                teamNameInput.focus();
                return;
            }

            const members = [];
            
            // Loop through all 4 possible operative sections
            for (let i = 1; i <= 4; i++) {
                const contentDiv = document.getElementById(`op-content-${i}`);
                if (contentDiv) {
                    const inputs = contentDiv.querySelectorAll('input[type="text"]');
                    if (inputs.length === 5) {
                        const name = inputs[0].value.trim();
                        const roll_number = inputs[1].value.trim();
                        const branch = inputs[2].value.trim();
                        const course = inputs[3].value.trim();
                        const study_year = inputs[4].value.trim();
                        
                        // If name is filled, assume they want to register this operative
                        // We will enforce that all fields must be filled for that operative
                        if (name !== "") {
                            if (!roll_number || !branch || !course || !study_year) {
                                alert(`ALERT: Operative #0${i} has incomplete data. All fields are required for active operatives.`);
                                return;
                            }
                            members.push({
                                name, roll_number, branch, course, study_year
                            });
                        }
                    }
                }
            }

            if (members.length < 2 || members.length > 4) {
                alert(`A cell requires between 2 and 4 operatives. You have provided ${members.length}.`);
                return;
            }

            registerBtn.disabled = true;
            const originalHTML = registerBtn.innerHTML;
            registerBtn.innerHTML = `
                <div class="flex flex-col items-center justify-center py-1">
                  <div class="flex items-center space-x-2 text-secondary">
                    <span class="material-symbols-outlined animate-spin text-[24px]">progress_activity</span>
                    <span class="font-headline-sm text-headline-sm uppercase">TRANSMITTING CELL DATA...</span>
                  </div>
                  <span class="font-label-hud text-label-hud text-primary tracking-widest mt-1">GENERATING CRYPTO KEY FOR [${teamName.toUpperCase()}]</span>
                </div>
            `;

            try {
                const res = await fetch("/register_team", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ team_name: teamName, members })
                });

                const data = await res.json();
                
                if (res.ok) {
                    // Success! Show QR Modal
                    registerBtn.innerHTML = `
                      <div class="flex flex-col items-center justify-center py-1">
                        <span class="font-headline-sm text-headline-sm text-tertiary uppercase">ROSTER COMMITTED // AUTHENTICATED</span>
                      </div>
                    `;
                    registerBtn.classList.remove('bg-primary-container');
                    registerBtn.classList.add('bg-tertiary-container');
                    
                    showQRModal(data.qr_code_hash, teamName);
                } else {
                    alert("Error: " + (data.detail || "Failed to initialize cell."));
                    registerBtn.disabled = false;
                    registerBtn.innerHTML = originalHTML;
                }
            } catch (e) {
                console.error("Network Error:", e);
                alert("Connection to host severed.");
                registerBtn.disabled = false;
                registerBtn.innerHTML = originalHTML;
            }
        });
    }
});

function toggleOperative(contentId, iconId) {
    const content = document.getElementById(contentId);
    const icon = document.getElementById(iconId);
    
    if (content.classList.contains('hidden')) {
    content.classList.remove('hidden');
    content.classList.add('block');
    icon.innerText = 'expand_less';
    icon.classList.remove('text-outline');
    icon.classList.add('text-secondary');
    } else {
    content.classList.add('hidden');
    content.classList.remove('block');
    icon.innerText = 'expand_more';
    icon.classList.add('text-outline');
    icon.classList.remove('text-secondary');
    }
}

function showQRModal(hash, teamName) {
    const modalHTML = `
    <div id="qr-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <div class="bg-surface-dim border border-primary p-6 max-w-sm w-full mx-4 relative neon-glow-primary">
            <h2 class="text-headline-md font-headline-md text-primary uppercase text-center mb-2">CELL INITIALIZED</h2>
            <p class="text-center font-code-terminal text-sm text-outline mb-4">ALIAS: ${teamName}</p>
            
            <div class="bg-white p-4 mx-auto w-max mb-4">
                <div id="qrcode"></div>
            </div>
            
            <p class="text-center font-code-terminal text-[10px] text-error mb-4 break-all">
                HASH: ${hash}
            </p>

            <button id="close-modal" class="w-full bg-primary-container text-on-primary-container py-2 font-code-terminal uppercase hover:bg-primary border border-primary transition-all shadow-[0_0_12px_rgba(176,38,255,0.4)]">
                DISMISS
            </button>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHTML);

    if (typeof QRCode === "undefined") {
        const script = document.createElement('script');
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
        script.onload = () => {
            new QRCode(document.getElementById("qrcode"), {
                text: hash,
                width: 200,
                height: 200,
                colorDark: "#000000",
                colorLight: "#ffffff"
            });
        };
        document.head.appendChild(script);
    } else {
        new QRCode(document.getElementById("qrcode"), {
            text: hash,
            width: 200,
            height: 200,
            colorDark: "#000000",
            colorLight: "#ffffff"
        });
    }

    document.getElementById("close-modal").addEventListener("click", () => {
        // Just reload the page when dismissed to reset everything
        window.location.reload();
    });
}
