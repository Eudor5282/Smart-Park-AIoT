const aiZoneState = {};

function getCameraOrigin() {
  // ใช้ origin เดียวกับหน้าเว็บเสมอ (relative to same host) เพราะ Flask
  // เสิร์ฟทั้งหน้าเว็บและ API จาก service เดียวกัน — เดิม hardcode ไปที่
  // 127.0.0.1:5000 ซึ่งใช้ไม่ได้เมื่อ deploy ผ่าน Docker/Coolify (proxy ที่
  // 80/443 ไม่ใช่ 5000)
  return window.location.origin;
}

function formatDuration(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h} ชม. ${m} นาที`;
  if (m > 0) return `${m} นาที ${sec} วิ`;
  return `${sec} วินาที`;
}

async function pollCam() {
  const cameraOrigin = getCameraOrigin();
  const urls = [`${cameraOrigin}/video`];

  let lastError = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, { cache: 'no-store' });
      if (res.ok) {
        return await res.json();
      }
      lastError = new Error(`HTTP ${res.status} from ${url}`);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('Camera endpoint unavailable');
}

window.sendUltrasonicStateToCameraServer = async function sendUltrasonicStateToCameraServer(slots) {
  const payloadSlots = {};

  for (const slot of slots || []) {
    const id = slot?.id;
    if (!id) continue;
    const status = String(slot?.status ?? '').trim().toLowerCase();
    payloadSlots[id] = ['occupied', 'sensor error', 'overtime parking'].includes(status)
      ? 'occupied'
      : 'empty';
  }

  try {
    await fetch(`${getCameraOrigin()}/ultrasonic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slots: payloadSlots }),
      cache: 'no-store'
    });
  } catch (error) {
    // Keep backend communication safe
  }
};

function getMode() {
  return localStorage.getItem('smartParkingMode') || 'board';
}

function shouldRunTestMode() {
  return true;
}

function ensureElements() {
  const existingImg = document.getElementById('camAiImg');
  if (existingImg) {
    return;
  }

  const wrap = document.createElement('div');
  wrap.id = 'camAiWrapper';
  wrap.className = 'bg-zinc-900/90 border border-zinc-800 p-4 shadow-xl mt-6';

  wrap.innerHTML = `
    <div class="flex items-center gap-2 mb-3 border-b border-zinc-800 pb-2">
      <span class="w-2 h-2 bg-cyan-400 rounded-full"></span>
      <h3 class="font-orbitron font-bold text-sm tracking-widest uppercase text-cyan-400">AI Camera (Block 4)</h3>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="flex flex-col">
        <img id="camAiImg" class="w-full border border-zinc-800" style="max-height:240px; object-fit:cover;" />
        <div class="mt-2 text-xs text-gray-500 font-mono" id="camAiFps">FPS: -</div>
        <div class="mt-1 text-[11px] text-gray-600 font-mono" id="camAiTs">-</div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div class="bg-zinc-900/40 border border-zinc-800 p-3">
          <div class="text-xs text-gray-400 uppercase font-mono">P1</div>
          <div class="text-2xl font-orbitron font-black" id="camAiStatus-P1">-</div>
          <div class="text-xs text-gray-500 font-mono" id="camAiConf-P1">0%</div>
        </div>
        <div class="bg-zinc-900/40 border border-zinc-800 p-3">
          <div class="text-xs text-gray-400 uppercase font-mono">P2</div>
          <div class="text-2xl font-orbitron font-black" id="camAiStatus-P2">-</div>
          <div class="text-xs text-gray-500 font-mono" id="camAiConf-P2">0%</div>
        </div>
        <div class="bg-zinc-900/40 border border-zinc-800 p-3">
          <div class="text-xs text-gray-400 uppercase font-mono">P3</div>
          <div class="text-2xl font-orbitron font-black" id="camAiStatus-P3">-</div>
          <div class="text-xs text-gray-500 font-mono" id="camAiConf-P3">0%</div>
        </div>
        <div class="bg-zinc-900/40 border border-zinc-800 p-3">
          <div class="text-xs text-gray-400 uppercase font-mono">P4</div>
          <div class="text-2xl font-orbitron font-black" id="camAiStatus-P4">-</div>
          <div class="text-xs text-gray-500 font-mono" id="camAiConf-P4">0%</div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(wrap);
}

function mapStatus(status) {
  if (status === 'Occupied') return 'ไม่ว่าง';
  if (status === 'Empty') return 'ว่าง';
  if (status === 'NotCar') return 'ไม่ใช่รถ';
  if (status === 'Pending') return 'กำลังยืนยัน';
  if (status === 'NoClassifier') return 'NO AI';
  return status;
}

function getUltrasonicState(rawValue) {
  // เดิมฟังก์ชันนี้อ่านจาก window.smartParkingLatestBoardStatus ซึ่งเป็น
  // ตัวแปรที่จะมีค่าก็ต่อเมื่อกดปุ่ม "เชื่อมต่อบอร์ดผ่าน Wi-Fi" (โหมดทดสอบ
  // LAN แบบเก่า) เท่านั้น — ถ้าไม่เคยกด/กดแล้วไม่สำเร็จ ตัวแปรนี้จะว่าง
  // เปล่าตลอด ทำให้ทุกช่องถูกบังคับให้เป็น "ว่าง" เสมอ ไม่ว่า backend จะ
  // สรุปผลว่าอย่างไรก็ตาม แก้ให้อ่านค่า ultrasonic ตรงจาก payload ของ
  // /video (preds.ultrasonic) แทน ซึ่งเป็นค่าจริงที่บอร์ดส่งเข้ามาแล้ว
  if (rawValue === undefined || rawValue === null) {
    return null;
  }

  const text = String(rawValue).trim().toLowerCase();
  if (['ว่าง', 'empty'].includes(text)) {
    return 'empty';
  }
  if (['ไม่ว่าง', 'occupied', 'overtime parking', 'sensor error'].includes(text)) {
    return 'occupied';
  }
  return null;
}

function decideZoneState(zoneId, cameraStatus, cameraConfidence, ultrasonicRaw) {
  const ultraState = getUltrasonicState(ultrasonicRaw);
  const state = aiZoneState[zoneId] || {
    lastDecision: 'Empty',
    confirmedOccupied: false,
    emptySince: null,
    occupiedSince: null,
    occupiedCount: 0,
    notCarCount: 0,
    displayConfidence: 0
  };
  const confidence = Number(cameraConfidence || 0);

  if (ultraState === 'empty') {
    state.confirmedOccupied = false;
    state.occupiedCount = 0;
    state.notCarCount = 0;
    state.lastDecision = 'Empty';
    state.displayConfidence = 0;
    aiZoneState[zoneId] = state;
    return { status: state.lastDecision, confidence: state.displayConfidence };
  }

  if (ultraState !== 'occupied') {
    aiZoneState[zoneId] = state;
    return { status: 'Empty', confidence: 0 };
  }

  // ป้องกันการกระพริบโดยใช้ตัวกรองถ่วงดุลค่าลอจิก 3 รอบเฟรมต่อเนื่อง
  if (cameraStatus === 'Occupied') {
    state.occupiedCount++;
    state.notCarCount = 0;
    if (state.occupiedCount >= 3) {
      state.confirmedOccupied = true;
      state.lastDecision = 'Occupied';
    }
    state.displayConfidence = confidence;
  } else if (cameraStatus === 'NotCar') {
    state.notCarCount++;
    state.occupiedCount = 0;
    if (state.notCarCount >= 3) {
      state.confirmedOccupied = false;
      state.lastDecision = 'NotCar';
    }
    state.displayConfidence = confidence;
  } else if (cameraStatus === 'NoClassifier') {
    state.lastDecision = 'NoClassifier';
    state.displayConfidence = 0;
  } else {
    if (!state.confirmedOccupied && state.lastDecision !== 'NotCar') {
      state.lastDecision = 'Pending';
    }
    state.displayConfidence = confidence;
  }

  aiZoneState[zoneId] = state;
  return { status: state.lastDecision, confidence: state.displayConfidence };
}

function isCarStatus(status) {
  return status === 'Occupied';
}

function slotDisplay(status) {
  if (status === 'Empty') return { text: 'ว่าง', badge: 'ว่าง' };
  if (status === 'Occupied') return { text: 'ไม่ว่าง', badge: 'ไม่ว่าง' };
  if (status === 'NotCar') return { text: 'ไม่ใช่รถ', badge: 'ไม่ใช่รถ' };
  if (status === 'NoClassifier') return { text: 'NO AI', badge: 'NO AI' };
  return { text: 'กำลังยืนยัน', badge: 'CHECKING' };
}

function applyAiSlotCard(zoneId, status, confidence) {
  const card = document.getElementById(`card-${zoneId}`);
  const statusEl = document.getElementById(`status-${zoneId}`);
  const badge = document.getElementById(`badge-${zoneId}`);
  const confidenceEl = document.getElementById(`confidence-${zoneId}`);
  if (!card || !statusEl || !badge || !confidenceEl) return;

  const display = slotDisplay(status);
  card.className = 'bg-zinc-900/40 border-2 border-zinc-800 p-8 transition-all duration-300 relative flex flex-col justify-between min-h-[240px]';
  badge.className = 'px-3 py-1 font-orbitron text-xs tracking-widest uppercase font-bold ';
  statusEl.className = 'text-3xl font-bold font-orbitron tracking-wide mt-1 ';

  if (status === 'Empty') {
    card.classList.add('neon-border-green');
    statusEl.classList.add('text-green-400');
    badge.classList.add('bg-green-500/20', 'text-green-400');
    confidenceEl.className = 'font-mono font-bold text-green-400';
  } else if (status === 'Occupied') {
    card.classList.add('neon-border-red');
    statusEl.classList.add('text-red-500');
    badge.classList.add('bg-red-500/20', 'text-red-500');
    confidenceEl.className = 'font-mono font-bold text-red-500';
  } else {
    card.classList.add('neon-border-yellow');
    statusEl.classList.add('text-yellow-500');
    badge.classList.add('bg-yellow-500/20', 'text-yellow-500');
    confidenceEl.className = 'font-mono font-bold text-yellow-500';
  }

  statusEl.textContent = display.text;
  badge.textContent = display.badge;
  confidenceEl.textContent = `${Math.round(Number(confidence || 0) * 100)} %`;
}

function updateAiSummary(zoneDecisions) {
  const availableEl = document.getElementById('totalAvailable');
  const recommendedEl = document.getElementById('aiRecommended');
  if (!availableEl || !recommendedEl) return;

  const ids = ['P1', 'P2', 'P3', 'P4'];
  const available = ids.filter(id => zoneDecisions[id]?.status === 'Empty').length;
  const recommended = ids.find(id => zoneDecisions[id]?.status === 'Empty') || '-';

  availableEl.textContent = available;
  recommendedEl.textContent = recommended;
}

function updateCamUI(payload) {
  const preds = payload?.preds;
  if (!preds) return;

  const cam = preds.camera;
  if (cam && cam.opened === false) {
    for (const zid of ['P1','P2','P3','P4']) {
      const statusEl = document.getElementById(`camAiStatus-${zid}`);
      const confEl = document.getElementById(`camAiConf-${zid}`);
      if (statusEl) statusEl.textContent = 'CAM OPEN FAILED';
      if (confEl) confEl.textContent = `${cam.reason || ''}`;
    }
    return;
  }

  const fps = preds.fps ?? 0;
  const ts = preds.ts ? new Date(preds.ts * 1000).toLocaleTimeString() : '-';
  const zones = preds.zones || {};
  const ultrasonic = preds.ultrasonic || {};

  const img = document.getElementById('camAiImg');
  if (img) {
    if (payload.img) {
      img.src = `data:image/jpeg;base64,${payload.img}`;
    } else {
      img.alt = 'Waiting for camera stream';
    }
  }

  document.getElementById('camAiFps').textContent = `FPS: ${fps.toFixed(1)}`;
  document.getElementById('camAiTs').textContent = `TS: ${ts}`;

  const zoneDecisions = {};
  for (const zid of ['P1', 'P2', 'P3', 'P4']) {
    const z = zones[zid] || {};
    const conf = Number(z?.confidence ?? 0);
    const decision = decideZoneState(zid, z?.status, conf, ultrasonic[zid]);
    const st = decision.status;
    const displayConfidence = Number(decision.confidence ?? 0);
    zoneDecisions[zid] = { status: st, confidence: displayConfidence };

    applyAiSlotCard(zid, st, displayConfidence);

    const statusEl = document.getElementById(`camAiStatus-${zid}`);
    const confEl = document.getElementById(`camAiConf-${zid}`);

    if (statusEl) statusEl.textContent = mapStatus(st);
    if (confEl) confEl.textContent = `${(displayConfidence * 100).toFixed(0)}%`;

    const occupiedSince = z?.occupied_since;
    let sinceText = '-';
    let durationText = '-';
    if (occupiedSince) {
      const sinceDate = new Date(occupiedSince * 1000);
      const elapsedSec = (Date.now() / 1000) - occupiedSince;
      sinceText = `จอดตั้งแต่ ${sinceDate.toLocaleTimeString()}`;
      durationText = `จอดมาแล้ว ${formatDuration(elapsedSec)}`;
    }

    // อัปเดตทั้งช่อง log เล็ก (AI Camera panel) และการ์ดสถานะใหญ่ (P1-P4)
    const sinceEl = document.getElementById(`camAiSince-${zid}`);
    const durationEl = document.getElementById(`camAiDuration-${zid}`);
    if (sinceEl) sinceEl.textContent = sinceText;
    if (durationEl) durationEl.textContent = durationText;

    const cardSinceEl = document.getElementById(`parkedSince-${zid}`);
    const cardDurationEl = document.getElementById(`parkedDuration-${zid}`);
    if (cardSinceEl) cardSinceEl.textContent = sinceText;
    if (cardDurationEl) cardDurationEl.textContent = durationText;
  }

  updateAiSummary(zoneDecisions);
}

async function fetchHistory() {
  const cameraOrigin = getCameraOrigin();
  const res = await fetch(`${cameraOrigin}/history`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data?.records || [];
}

function renderPeakChart(records) {
  const container = document.getElementById('peakChartContainer');
  const labelsRow = document.getElementById('peakChartLabels');
  const peakText = document.getElementById('peakHourText');
  const offPeakText = document.getElementById('offPeakHourText');
  if (!container || !labelsRow) return;

  // รวมนาทีจอดทั้งหมด แบ่งตามชั่วโมงของวัน (0-23) จากทุกช่องรวมกัน
  const hourMinutes = new Array(24).fill(0);

  for (const rec of records) {
    const startSec = Number(rec?.start_ts ?? 0);
    const durationSec = Number(rec?.duration_sec ?? 0);
    if (!startSec || durationSec <= 0) continue;
    const hour = new Date(startSec * 1000).getHours();
    hourMinutes[hour] += durationSec / 60;
  }

  const maxMinutes = Math.max(...hourMinutes);

  if (!records.length || maxMinutes <= 0) {
    container.innerHTML = '<p class="text-xs text-gray-600 italic m-auto">ยังไม่มีข้อมูลประวัติการจอด</p>';
    labelsRow.innerHTML = '';
    if (peakText) peakText.textContent = '-';
    if (offPeakText) offPeakText.textContent = '-';
    return;
  }

  let peakHour = 0;
  let offPeakHour = 0;
  for (let h = 0; h < 24; h++) {
    if (hourMinutes[h] > hourMinutes[peakHour]) peakHour = h;
    if (hourMinutes[h] < hourMinutes[offPeakHour]) offPeakHour = h;
  }

  if (peakText) peakText.textContent = `${String(peakHour).padStart(2, '0')}:00 - ${String((peakHour + 1) % 24).padStart(2, '0')}:00`;
  if (offPeakText) offPeakText.textContent = `${String(offPeakHour).padStart(2, '0')}:00 - ${String((offPeakHour + 1) % 24).padStart(2, '0')}:00`;

  container.innerHTML = '';
  labelsRow.innerHTML = '';

  for (let h = 0; h < 24; h++) {
    const heightPct = maxMinutes > 0 ? Math.max(2, (hourMinutes[h] / maxMinutes) * 100) : 2;
    const isPeak = h === peakHour && hourMinutes[h] > 0;

    const bar = document.createElement('div');
    bar.className = `flex-1 rounded-t-sm transition-all duration-300 ${isPeak ? 'bg-red-500' : 'bg-cyan-500/60'}`;
    bar.style.height = `${heightPct}%`;
    bar.title = `${String(h).padStart(2, '0')}:00 — ${hourMinutes[h].toFixed(1)} นาทีรวม`;
    container.appendChild(bar);

    const label = document.createElement('div');
    label.className = 'flex-1 text-center';
    label.textContent = h % 3 === 0 ? h : '';
    labelsRow.appendChild(label);
  }
}

async function historyLoop() {
  while (true) {
    try {
      const records = await fetchHistory();
      renderPeakChart(records);
    } catch (e) {
      // Catch error silently — chart just stays at last known state
    }
    await new Promise(r => setTimeout(r, 30000));
  }
}

async function start() {
  ensureElements();
  historyLoop();

  while (true) {
    if (!shouldRunTestMode()) {
      await new Promise(r => setTimeout(r, 250));
      continue;
    }

    try {
      const payload = await pollCam();
      updateCamUI(payload);
    } catch (e) {
      // Catch error silently
    }
    // ลดความถี่ poll จาก 200ms เป็น 400ms เพื่อลดภาระ CPU/RAM ของเครื่อง
    // (ช่วยลดโอกาสที่เบราว์เซอร์จะ discard/reload tab ตอนเครื่องโหลดหนัก)
    await new Promise(r => setTimeout(r, 400));
  }
}

start();
