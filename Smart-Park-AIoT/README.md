> **📌 ถ้ากำลัง deploy ผ่าน Coolify ของโรงเรียน (คลาวด์ ไม่ใช่รันในเครื่อง
> อย่างเดียว) ให้อ่าน `DEPLOY-COOLIFY.md` และ `START-HERE-WINDOWS.md` แทน**
> README.md ไฟล์นี้อธิบายวิธีรันแบบ "host เครื่องเดียวในวง LAN" (ไม่มี
> คลาวด์เกี่ยวข้อง) ซึ่งเป็นคนละสถานการณ์กับตอนนี้ที่เว็บรันอยู่บนโดเมน
> สาธารณะของ Coolify แล้วต้องมี `camera_uploader.py` ช่วยส่งภาพกล้องเข้าไป
> (อ่านเหตุผลเต็ม ๆ ได้ในไฟล์ที่แนะนำด้านบน)

# Smart Car Parking — คู่มือรัน (Docker / Native)

ระบบนี้เป็น Flask server ตัวเดียว ที่:
- เปิดกล้อง USB ของเครื่องที่รันอยู่
- รันโมเดล AI (Teachable Machine) แยกช่องจอด 4 ช่อง (P1–P4)
- เสิร์ฟหน้าเว็บ (index.html) ในตัวเอง ที่พอร์ต **5000**
- รับข้อมูล ultrasonic จากบอร์ด Arduino ผ่าน `POST /ultrasonic`

**สถาปัตยกรรมสำคัญที่ต้องเข้าใจก่อน:**
มีเครื่องเดียวเท่านั้นที่ต้อง "รันเซิร์ฟเวอร์ + เปิดกล้อง" เรียกว่าเครื่อง **host**
เครื่องอื่นๆ ในวง Wi-Fi/LAN เดียวกัน **แค่เปิดเบราว์เซอร์** ไปที่ `http://<IP เครื่อง host>:5000`
ก็จะเห็นภาพกล้อง/สถานะช่องจอดเหมือนกันทันที (ไม่ต้องติดตั้งอะไรเลย ไม่ต้องมีกล้องของตัวเอง)
**ถ้าเครื่อง host ปิดหรือหยุดรัน เครื่องอื่นจะเข้าเว็บไม่ได้และไม่เห็นกล้องทันที** — ตรงตามที่เข้าใจไว้เป๊ะ

---

## ⚠️ ข้อจำกัดสำคัญ: Docker กับกล้อง USB

| Host OS | Docker เข้าถึงกล้อง USB ได้ไหม | วิธีที่แนะนำ |
|---|---|---|
| **Linux** (Ubuntu/Raspberry Pi) | ✅ ได้ตรงๆ | ใช้ Docker (`docker-compose.yml`) |
| **Windows** | ❌ Docker Desktop เข้าไม่ถึงกล้องโดยตรง | รัน native ด้วย `run_windows.bat` |
| **Mac** | ❌ Docker Desktop เข้าไม่ถึงกล้องโดยตรง | รัน native ด้วย `run_mac_linux.sh` |

นี่คือข้อจำกัดของตัว Docker Desktop เอง (มันรัน container ผ่าน VM เสมือนที่มองไม่เห็นฮาร์ดแวร์ USB ของเครื่องจริง) ไม่ใช่ปัญหาที่แก้ในโค้ดได้ ทุกโปรเจกต์ที่ใช้กล้อง USB เจอปัญหานี้เหมือนกันหมด

**สรุปง่ายๆ:** เพื่อนครูคนไหนใช้เครื่อง **Linux** → ใช้ Docker ได้เต็มที่ตามที่ตั้งใจไว้
ใครใช้ **Windows/Mac** → ใช้สคริปต์ native ที่เตรียมไว้ให้ (ยังคง "รันไฟล์เดียวจบ" เหมือนกัน แค่ไม่ใช่ Docker) ผลลัพธ์ที่ได้เหมือนกันทุกประการ — คนอื่นในวง LAN เปิดเว็บดูได้เหมือนกัน

---

## วิธีที่ 1: Linux (ใช้ Docker)

ต้องติดตั้ง [Docker](https://docs.docker.com/engine/install/) และ [Docker Compose](https://docs.docker.com/compose/install/) ก่อน

```bash
# 1. เสียบกล้อง USB แล้วเช็คว่าเครื่องเห็นกล้องเป็นชื่ออะไร
ls -l /dev/video*
# ปกติจะเป็น /dev/video0 — ถ้าเป็นเลขอื่น ให้แก้ไฟล์ docker-compose.yml
# บรรทัด devices: ให้ตรงกับที่เจอ

# 2. build และรัน (ครั้งแรกจะช้าเพราะโหลด TensorFlow ~1-2GB)
docker compose up --build -d

# 3. ดูสถานะ / log
docker compose logs -f

# 4. หยุดระบบ
docker compose down
```

หา IP ของเครื่อง host เพื่อบอกคนอื่น:
```bash
hostname -I
```
แล้วให้เครื่องอื่นเปิด `http://<IP ที่ได้>:5000`

---

## วิธีที่ 2: Windows (native, ไม่ใช้ Docker)

ต้องติดตั้ง [Python 3.10+](https://www.python.org/downloads/) ก่อน (ตอนติดตั้งติ๊ก "Add python.exe to PATH" ด้วย)

1. ดับเบิลคลิกไฟล์ **`run_windows.bat`**
2. รอครั้งแรกสักพัก (ติดตั้งไลบรารี + โหลด TensorFlow)
3. เมื่อเห็นข้อความ `Running on http://0.0.0.0:5000` แปลว่าพร้อมแล้ว
4. หา IP เครื่องนี้: เปิด cmd พิมพ์ `ipconfig` ดูช่อง **IPv4 Address**
5. บอกคนอื่นในวง Wi-Fi เดียวกันให้เปิด `http://<IP ที่ได้>:5000`

> ถ้าอยากใช้ Docker บน Windows จริงๆ (ขั้นสูง): ต้องติดตั้ง [usbipd-win](https://github.com/dorssel/usbipd-win)
> เพื่อ "แชร์" กล้อง USB เข้า WSL2 ก่อน แล้วค่อยรัน `docker compose up` ผ่าน Docker Desktop
> (WSL2 backend) โดย uncomment บรรทัด `devices:` ใน `docker-compose.yml` — ขั้นตอนซับซ้อนและ
> ต้องทำใหม่ทุกครั้งที่ถอด-เสียบกล้อง จึงแนะนำให้ใช้ `run_windows.bat` แทนถ้าไม่จำเป็นจริงๆ

---

## วิธีที่ 3: Mac (native, ไม่ใช้ Docker)

ต้องมี Python 3.10+ (เช็คด้วย `python3 --version`, หรือติดตั้งผ่าน `brew install python`)

```bash
chmod +x run_mac_linux.sh   # ทำครั้งแรกครั้งเดียว
./run_mac_linux.sh
```

macOS จะขึ้น popup ถามสิทธิ์เข้าถึงกล้อง ให้กด **Allow** (ถ้าพลาดกด Deny ไปแล้วให้เข้า
System Settings → Privacy & Security → Camera → เปิดสิทธิ์ให้ Terminal/python)

> หมายเหตุ Mac รุ่นชิป Apple Silicon (M1/M2/M3): ถ้าติดตั้ง `tensorflow` ปกติแล้วมีปัญหา
> ลองเปลี่ยนใน `requirements.txt` เป็น `tensorflow-macos` แทน

---

## Config ที่ปรับได้ (environment variables)

ปรับได้ทั้งตอนรัน Docker (แก้ใน `docker-compose.yml`) และตอนรัน native (ตั้งก่อนรัน เช่น
`set CAM_INDEX=1` บน Windows หรือ `export CAM_INDEX=1` บน Mac/Linux):

| ตัวแปร | ค่า default | ใช้ทำอะไร |
|---|---|---|
| `CAM_INDEX` | `0` | index ของกล้อง ถ้าเครื่องมีหลายกล้อง (เช่น มีทั้งกล้องในตัวโน้ตบุ๊กกับ USB) ลองเปลี่ยนเป็น 1, 2 |
| `CAP_WIDTH` | `640` | ความกว้างภาพที่ขอจากกล้อง |
| `CAP_HEIGHT` | `480` | ความสูงภาพที่ขอจากกล้อง |
| `PORT` | `5000` | พอร์ตที่เว็บเซิร์ฟเวอร์รัน |

---

## ตรวจสอบว่ากล้องเปิดสำเร็จหรือไม่

เปิด `http://<IP host>:5000/video` ตรงๆ ในเบราว์เซอร์ จะเห็น JSON เช่น
```json
{"preds": {"camera": {"opened": true, "reason": "ok"}, ...}}
```
ถ้า `opened: false` ให้ดู `reason` ประกอบ (เช่น `"open failed"` แปลว่าเครื่อง host หากล้องไม่เจอเลย
ให้เช็คว่ากล้องเสียบอยู่จริง และไม่มีโปรแกรมอื่นแย่งใช้กล้องอยู่)

## ไฟล์ในโปรเจกต์นี้ที่เพิ่มเข้ามาเพื่อทำ Docker/native

- `Dockerfile`, `docker-compose.yml`, `.dockerignore` — สำหรับรันบน Linux ผ่าน Docker
- `requirements.txt` — รายการไลบรารี (ใช้ร่วมกันทั้ง Docker และ native)
- `run_windows.bat`, `run_mac_linux.sh` — สคริปต์รัน native ให้ Windows/Mac
- `cam_ai_server.py` — แก้เพิ่มการอ่านค่า `CAM_INDEX` / `CAP_WIDTH` / `CAP_HEIGHT` / `PORT`
  จาก environment variable แทนที่จะ fix ค่าตายตัวในโค้ด (โค้ด logic เดิมไม่ถูกแก้เลย)
