let boardBaseUrl = localStorage.getItem('smartParkingBoardUrl') || 'http://smartparking.local';
let pollTimer = null;
let failedPolls = 0;
window.smartParkingLatestBoardStatus = {};
window.smartParkingSlotState = {};

const connectBtn = document.getElementById('connectBtn');
const btnText = document.getElementById('btnText');
const btnDot = document.getElementById('btnDot');
const serialStatusText = document.getElementById('serialStatusText');

const modeBtn = document.getElementById('modeBtn');
const modeBtnText = document.getElementById('modeBtnText');

function getMode() {
    return localStorage.getItem('smartParkingMode') || 'test';
}

function setMode(mode) {
    localStorage.setItem('smartParkingMode', mode);
    updateModeUI();

    if (mode === 'test') {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
        setConnectionState('disconnected');
    }
}

function updateModeUI() {
    const mode = getMode();
    if (modeBtnText) {
        if (mode === 'test') modeBtnText.textContent = 'MODE: Test mode (AI only)';
        if (mode === 'board') modeBtnText.textContent = 'MODE: Board mode (Ultrasonic)';
    }
}

updateModeUI();
setConnectionState('disconnected');

// หมายเหตุ: เดิมโหมด "Board mode" จะให้เบราว์เซอร์ของคนดูยิง fetch ตรงไปหา
// IP ของบอร์ด Arduino ในวง LAN โดยตรง ซึ่งใช้ไม่ได้อีกต่อไปเมื่อ deploy ผ่าน
// Coolify (HTTPS + โดเมนสาธารณะ) เพราะเบราว์เซอร์บล็อกการยิง request แบบนี้
// (Private Network Access) และคนดูจากที่อื่นก็ไม่มีทางเห็น IP วง local ได้
// ตอนนี้ข้อมูล ultrasonic ถูกส่งจากบอร์ด -> เซิร์ฟเวอร์กลาง (POST
// /ultrasonic) แล้วรวมเข้ากับข้อมูลกล้องที่ /video โดยอัตโนมัติอยู่แล้ว
// จึงปิดการเชื่อมต่ออัตโนมัตินี้ไว้ (ยังกดปุ่ม "เชื่อมต่อบอร์ดผ่าน Wi-Fi"
// เองได้เผื่อทดสอบตอนอยู่ในวง LAN เดียวกับบอร์ดจริง ๆ)
// if (getMode() === 'board') {
//     connectToBoard(true);
// }

if (modeBtn) {
    modeBtn.addEventListener('click', () => {
        const current = getMode();
        setMode(current === 'test' ? 'board' : 'test');
    });
}

connectBtn.addEventListener('click', async () => {
    if (getMode() !== 'board') {
        alert('สลับไปที่ Board mode (Ultrasonic) ก่อนเชื่อมต่อบอร์ด');
        return;
    }
    if (pollTimer) return;

    const input = prompt('ใส่ URL หรือ IP ของบอร์ด เช่น http://192.168.1.42', boardBaseUrl);
    if (!input) return;

    boardBaseUrl = normalizeBoardUrl(input);
    localStorage.setItem('smartParkingBoardUrl', boardBaseUrl);

    await connectToBoard(false);
});

async function connectToBoard(silent = false) {
    setConnectionState('connecting');

    try {
        await fetchBoardData();
        pollTimer = setInterval(pollBoardData, 700);
        setConnectionState('connected');
    } catch (error) {
        console.error('เชื่อมต่อ Wi-Fi telemetry ไม่สำเร็จ:', error);
        setConnectionState('disconnected');
        if (!silent) {
            alert(`เชื่อมต่อบอร์ดไม่สำเร็จ\n\nตรวจสอบว่า:\n1. คอมและบอร์ดอยู่ Wi-Fi เดียวกัน\n2. URL ถูกต้อง เช่น http://192.168.1.42\n3. เปิดดู ${boardBaseUrl}/data แล้วเห็น JSON`);
        }
    }
}

function normalizeBoardUrl(value) {
    let url = value.trim();
    if (!/^https?:\/\//i.test(url)) {
        url = `http://${url}`;
    }
    return url.replace(/\/+$/, '');
}

async function fetchBoardData() {
    const response = await fetch(`${boardBaseUrl}/data`, { cache: 'no-store' });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    updateDashboard(data);
}

async function pollBoardData() {
    try {
        await fetchBoardData();
        failedPolls = 0;
    } catch (error) {
        failedPolls++;
        console.warn('อ่านข้อมูลจากบอร์ดไม่สำเร็จ:', error);

        if (failedPolls >= 3) {
            clearInterval(pollTimer);
            pollTimer = null;
            setConnectionState('disconnected');
        }
    }
}

function setConnectionState(state) {
    btnDot.classList.remove('bg-red-500', 'bg-green-500', 'bg-yellow-500', 'animate-pulse');
    serialStatusText.classList.remove('text-red-500', 'text-green-500', 'text-yellow-500');

    if (state === 'connected') {
        failedPolls = 0;
        btnDot.classList.add('bg-green-500');
        btnText.textContent = 'เชื่อมต่อ Wi-Fi สำเร็จ';
        serialStatusText.textContent = 'CONNECTED';
        serialStatusText.classList.add('text-green-500');
        connectBtn.disabled = true;
        connectBtn.style.opacity = '0.7';
        return;
    }

    if (state === 'connecting') {
        btnDot.classList.add('bg-yellow-500', 'animate-pulse');
        btnText.textContent = 'กำลังเชื่อมต่อ Wi-Fi...';
        serialStatusText.textContent = 'CONNECTING';
        serialStatusText.classList.add('text-yellow-500');
        connectBtn.disabled = true;
        connectBtn.style.opacity = '0.7';
        return;
    }

    btnDot.classList.add('bg-red-500', 'animate-pulse');
    btnText.textContent = 'เชื่อมต่อบอร์ดผ่าน Wi-Fi';
    serialStatusText.textContent = 'DISCONNECTED';
    serialStatusText.classList.add('text-red-500');
    connectBtn.disabled = false;
    connectBtn.style.opacity = '1';
}

function normalizeSlotStatus(value) {
    const text = String(value ?? '').trim().toLowerCase();
    if (['ว่าง', 'empty'].includes(text)) return 'Empty';
    if (['ไม่ว่าง', 'occupied', 'overtime parking', 'sensor error'].includes(text)) return 'Occupied';
    if (['notcar', 'not_car', 'not car'].includes(text)) return 'NotCar';
    return 'Unknown';
}

function resolveStableSlotStatus(slotId, incomingStatus) {
    const state = window.smartParkingSlotState[slotId] || { current: 'Unknown', pending: 'Unknown', count: 0 };
    const normalized = normalizeSlotStatus(incomingStatus);

    if (normalized === 'Unknown' || normalized === state.current) {
        state.pending = normalized;
        state.count = 0;
        state.current = normalized;
        window.smartParkingSlotState[slotId] = state;
        return state.current;
    }

    if (state.pending !== normalized) {
        state.pending = normalized;
        state.count = 1;
    } else {
        state.count += 1;
    }

    if (state.count >= 3) {
        state.current = state.pending;
        state.count = 0;
    }

    window.smartParkingSlotState[slotId] = state;
    return state.current;
}

function updateDashboard(jsonData) {
    // โน้ต: ย้ายหน้าที่การแก้ไขข้อความใน totalAvailable และ aiRecommended ให้ cam_ui เป็นคนจัดสรรร่วมกัน
    const timestamp = new Date().toLocaleTimeString();

    jsonData.slots.forEach(slot => {
        const slotId = slot.id;
        const incomingStatus = slot.status;
        const confidence = slot.confidence;
        const stableStatus = resolveStableSlotStatus(slotId, incomingStatus);
        window.smartParkingLatestBoardStatus[slotId] = stableStatus;

        let statusBadgeText = stableStatus === 'Empty' ? 'ว่าง' : stableStatus === 'Occupied' ? 'ไม่ว่าง' : 'UNKNOWN';
        let actionText = stableStatus === 'Empty' ? "แสดงไฟสถานะว่าง" : stableStatus === 'Occupied' ? "แสดงไฟสถานะมีรถจอด" : "ตรวจสอบฮาร์ดแวร์";

        // --- จุดแก้ไขสำคัญ ---
        // ถ้าหน้าเว็บมีสคริปต์กล้องทำงานอยู่ (ตรวจจับจากฟังก์ชันใน window) 
        // เราจะไม่เอาค่าจากฮาร์ดแวร์เพียวๆ ไปเขียนทับหน้าการแสดงผลบล็อกใหญ่เพื่อป้องกันการกระพริบชนกัน
        if (typeof window.sendUltrasonicStateToCameraServer !== 'function') {
            const card = document.getElementById(`card-${slotId}`);
            const statusEl = document.getElementById(`status-${slotId}`);
            const badge = document.getElementById(`badge-${slotId}`);
            const confidenceEl = document.getElementById(`confidence-${slotId}`);

            if (card && statusEl && badge && confidenceEl) {
                card.className = "bg-zinc-900/40 border-2 border-zinc-800 p-8 transition-all duration-300 relative flex flex-col justify-between min-h-[240px]";
                badge.className = "px-3 py-1 font-orbitron text-xs tracking-widest uppercase font-bold ";
                statusEl.className = "text-3xl font-bold font-orbitron tracking-wide mt-1 ";

                if (stableStatus === 'Empty') {
                    card.classList.add('neon-border-green');
                    statusEl.classList.add('text-green-400');
                    statusEl.textContent = "ว่าง";
                    badge.classList.add('bg-green-500/20', 'text-green-400');
                    confidenceEl.className = "font-mono font-bold text-green-400";
                } else if (stableStatus === 'Occupied') {
                    card.classList.add('neon-border-red');
                    statusEl.classList.add('text-red-500');
                    statusEl.textContent = "ไม่ว่าง";
                    badge.classList.add('bg-red-500/20', 'text-red-500');
                    confidenceEl.className = "font-mono font-bold text-red-500";
                } else {
                    card.classList.add('neon-border-yellow');
                    statusEl.classList.add('text-yellow-500');
                    statusEl.textContent = "ไม่เสถียร";
                    badge.classList.add('bg-yellow-500/20', 'text-yellow-500');
                    confidenceEl.className = "font-mono font-bold text-yellow-500";
                }
                badge.textContent = statusBadgeText;
                confidenceEl.textContent = `${confidence} %`;
            }
        }

        pushSensorLog(timestamp, slotId, statusBadgeText);
        pushAiLog(timestamp, slotId, statusBadgeText, confidence, actionText);
    });

    if (typeof window.sendUltrasonicStateToCameraServer === 'function') {
        window.sendUltrasonicStateToCameraServer(jsonData.slots);
    }
}

function pushSensorLog(time, id, status) {
    const tbody = document.getElementById('sensorLogBody');
    if (!tbody) return;
    if (tbody.rows.length === 1 && tbody.rows[0].cells.length === 1) tbody.innerHTML = "";

    let statusColor = "text-gray-400";
    if (status === "ว่าง") statusColor = "text-green-400";
    if (status === "ไม่ว่าง") statusColor = "text-red-500";
    if (status === "ERROR") statusColor = "text-yellow-500";

    const row = document.createElement('tr');
    row.className = "border-b border-zinc-800/40 hover:bg-zinc-800/20";
    row.innerHTML = `
        <td class="py-2 text-zinc-500">${time}</td>
        <td class="py-2 font-bold text-white">${id}</td>
        <td class="py-2 text-right font-bold ${statusColor}">${status}</td>
    `;
    tbody.insertBefore(row, tbody.firstChild);
    if (tbody.rows.length > 50) tbody.removeChild(tbody.lastChild);
}

function pushAiLog(time, id, status, conf, action) {
    const tbody = document.getElementById('aiLogBody');
    if (!tbody) return;
    if (tbody.rows.length === 1 && tbody.rows[0].cells.length === 1) tbody.innerHTML = "";

    let actionColor = "text-purple-400";
    if (status === "Overtime Parking") actionColor = "text-red-500 font-bold";
    if (status === "ERROR") actionColor = "text-yellow-600";

    const row = document.createElement('tr');
    row.className = "border-b border-zinc-800/40 hover:bg-zinc-800/20";
    row.innerHTML = `
        <td class="py-2 text-zinc-500">${time}</td>
        <td class="py-2 font-bold text-white">${id}</td>
        <td class="py-2 text-zinc-400">${conf}%</td>
        <td class="py-2 text-right ${actionColor}">${action}</td>
    `;
    tbody.insertBefore(row, tbody.firstChild);
    if (tbody.rows.length > 50) tbody.removeChild(tbody.lastChild);
}