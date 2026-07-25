// =========================================================
// เดิมไฟล์นี้ทำหน้าที่ให้ browser ผู้ใช้ fetch เข้า IP บอร์ด Arduino ตรงๆ
// (เช่น http://192.168.1.42/data) วิธีนี้ใช้ไม่ได้แล้วหลัง deploy ขึ้นคลาวด์
// (Coolify) เพราะ browser บล็อกการยิง request จาก origin คลาวด์เข้าหา IP
// วง local ของผู้ใช้ (Private Network Access) — เห็น error
// "blocked by CORS policy ... more-private address space" ใน console
//
// ตอนนี้บอร์ด Arduino ยิง POST /ultrasonic เข้าเซิร์ฟเวอร์ตรงเองแล้ว (ดู
// SmartCarParking n.ino) หน้าเว็บจึงไม่ต้องรู้จัก/เชื่อมต่อ IP บอร์ดอีกต่อไป
// ข้อมูลทั้งหมดมาทาง /video (same-origin) ที่ cam_ui_inject.js เป็นคนดึงและ
// แสดงผลอยู่แล้ว ไฟล์นี้เหลือแค่:
//   1) ตัวแสดงไฟสถานะเชื่อมต่อ (เรียกจาก cam_ui_inject.js)
//   2) ตาราง log สองอัน (Sensor Log / AI Log) ที่ cam_ui_inject.js เติมข้อมูลให้
// =========================================================

const connectBtn = document.getElementById('connectBtn');
const btnDot = document.getElementById('btnDot');
const serialStatusText = document.getElementById('serialStatusText');
const modeBtn = document.getElementById('modeBtn');

// ปุ่ม "เชื่อมต่อบอร์ดผ่าน Wi-Fi" และปุ่มสลับโหมดไม่จำเป็นอีกต่อไป เพราะ
// บอร์ดส่งข้อมูลเข้าเซิร์ฟเวอร์เองอัตโนมัติเสมอ ไม่ต้องกรอก IP จาก browser
// ซ่อนไว้แทนการลบออกจาก index.html เผื่ออยากเอากลับมาทีหลัง
if (connectBtn) connectBtn.style.display = 'none';
if (modeBtn) modeBtn.style.display = 'none';

function setConnectionState(state) {
    if (!btnDot || !serialStatusText) return;
    btnDot.classList.remove('bg-red-500', 'bg-green-500', 'bg-yellow-500', 'animate-pulse');
    serialStatusText.classList.remove('text-red-500', 'text-green-500', 'text-yellow-500');

    if (state === 'connected') {
        btnDot.classList.add('bg-green-500');
        serialStatusText.textContent = 'CONNECTED';
        serialStatusText.classList.add('text-green-500');
        return;
    }

    btnDot.classList.add('bg-red-500', 'animate-pulse');
    serialStatusText.textContent = 'DISCONNECTED';
    serialStatusText.classList.add('text-red-500');
}

// cam_ui_inject.js เรียกฟังก์ชันนี้ทุกครั้งที่ดึง /video สำเร็จ/ไม่สำเร็จ
// เพื่อสะท้อนสถานะการเชื่อมต่อกับเซิร์ฟเวอร์ (ไม่ใช่กับตัวบอร์ดโดยตรงอีกแล้ว)
window.smartParkingSetConnected = function (connected) {
    setConnectionState(connected ? 'connected' : 'disconnected');
};

setConnectionState('disconnected');

// ---- ตาราง log: เรียกใช้จาก cam_ui_inject.js ทุกครั้งที่มีผลลัพธ์ zone ใหม่ ----
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

window.pushSensorLog = pushSensorLog;
window.pushAiLog = pushAiLog;
