# START-HERE-WINDOWS.md
คู่มือสำหรับสิ่งที่ต้องการ: **เปิดคอมของฉันเป็น server ต่อ WiFi แล้วเครื่อง
อื่นในวงเดียวกันเข้าเว็บมาดูเหมือนกันได้**

อ่านให้จบก่อนเริ่มทำ มี 3 ส่วน:
- **ส่วน A** — วิธีที่ทำได้จริงชัวร์ที่สุด แนะนำให้เริ่มจากตรงนี้ (ใช้ Docker
  ตรง ๆ บน Windows ยังไม่ต้องยุ่งกับ Coolify)
- **ส่วน B** — ถ้าครูต้องการเห็นว่าใช้ Coolify จริง ๆ ต้องทำเพิ่มยังไง
- **ส่วน C** — ทำไมกล้องต้องมีสคริปต์แยกช่วย (อธิบายเหตุผลสั้น ๆ)

---

## ส่วน A: รันด้วย Docker บน Windows ตรง ๆ (ทำก่อน แนะนำสุด)

### A1) ติดตั้ง Docker Desktop
1. โหลดที่ https://www.docker.com/products/docker-desktop/ แล้วติดตั้ง
2. ตอนติดตั้งจะถามเรื่อง WSL2 ให้กด "ใช้ WSL2" (ค่าเริ่มต้นอยู่แล้ว)
3. ติดตั้งเสร็จแล้ว "รีสตาร์ทเครื่อง" ตามที่มันขอ
4. เปิด Docker Desktop ขึ้นมารอจนสถานะขึ้นเป็นสีเขียว/"Running"

### A2) เตรียมโปรเจกต์
วางโฟลเดอร์โปรเจกต์ (ที่มี `Dockerfile` อยู่) ไว้ที่ไหนก็ได้บนเครื่อง เช่น
`C:\Users\<ชื่อคุณ>\Desktop\SmartCarParkingNew`

### A3) สั่งรัน
เปิด **Command Prompt** หรือ **PowerShell** แล้ว `cd` เข้าไปในโฟลเดอร์นั้น
เช่น:

```powershell
cd C:\Users\<ชื่อคุณ>\Desktop\SmartCarParkingNew
docker compose up --build
```

รอบแรกจะช้าหน่อย (โหลด TensorFlow ~600MB) รอจนเห็น log ประมาณ

```
Listening at: http://0.0.0.0:5000
```

**ปล่อยหน้าต่างนี้รันค้างไว้ ห้ามปิด** (นี่คือ "server" ของคุณ)

ลองเปิดเบราว์เซอร์ที่เครื่องเดียวกันไปที่ `http://localhost:5000` ควรเห็น
หน้าเว็บ (ตอนนี้ยังไม่มีภาพจากกล้อง เพราะยังไม่ได้รันสคริปต์กล้องในขั้น A4)

### A4) เปิดกล้อง (รันสคริปต์แยกอีกหน้าต่าง)
เว็บแคมต้องมีสคริปต์ช่วยส่งภาพเข้า container (เหตุผลอยู่ในส่วน C) เปิด
Command Prompt/PowerShell **หน้าต่างใหม่อีกอัน** (อย่าปิดหน้าต่างเดิมที่รัน
`docker compose up`) แล้วรัน:

```powershell
cd C:\Users\<ชื่อคุณ>\Desktop\SmartCarParkingNew
pip install opencv-python requests
python camera_uploader.py
```

ถ้าเห็น log แบบนี้คือสำเร็จ:
```
[uploader] เปิดกล้องสำเร็จ กำลังส่งภาพไปที่ http://localhost:5000/frame
```

กลับไปรีเฟรชหน้าเว็บ `http://localhost:5000` ตอนนี้ควรเห็นภาพจากกล้องแล้ว

**สรุป: ต้องเปิดค้างไว้ 2 หน้าต่างพร้อมกันตลอดเวลา**
1. `docker compose up` (ตัวเซิร์ฟเวอร์หลัก)
2. `python camera_uploader.py` (ตัวส่งภาพกล้อง)

### A5) หาที่อยู่ (IP) ของคอมตัวเองในวง WiFi
เปิด Command Prompt อีกหน้าต่าง แล้วพิมพ์:

```powershell
ipconfig
```

มองหาหัวข้อ **Wireless LAN adapter Wi-Fi** แล้วดูค่า **IPv4 Address** เช่น
`192.168.1.25` (ของแต่ละคนจะไม่เหมือนกัน จำเลขนี้ไว้)

### A6) เปิด Windows Firewall ให้ port 5000
ค่าเริ่มต้น Windows Firewall จะบล็อกเครื่องอื่นเข้ามาที่ port 5000 ให้เปิด:

1. เปิด **Windows Defender Firewall with Advanced Security** (พิมพ์ค้นหาใน
   Start menu)
2. ซ้ายมือ → **Inbound Rules** → ขวามือ → **New Rule...**
3. เลือก **Port** → Next
4. เลือก **TCP** → ใส่ **Specific local ports:** `5000` → Next
5. เลือก **Allow the connection** → Next
6. ติ๊กทุกช่อง (Domain/Private/Public) → Next
7. ตั้งชื่อ เช่น `SmartCarParking` → Finish

### A7) เข้าจากเครื่องอื่นในวง WiFi เดียวกัน
บนมือถือ/โน้ตบุ๊กเครื่องอื่นที่ต่อ **WiFi วงเดียวกัน** กับคอมเซิร์ฟเวอร์ เปิด
เบราว์เซอร์แล้วพิมพ์:

```
http://<IP ที่ได้จาก A5>:5000
```

เช่น `http://192.168.1.25:5000` ควรเห็นหน้าเว็บเดียวกับที่เห็นบนคอมเซิร์ฟเวอร์
เลย รวมถึงภาพจากกล้องด้วย

> ข้อควรระวัง: IP นี้จะเปลี่ยนได้ถ้า router แจก IP ใหม่ (เช่น router รีสตาร์ท)
> ถ้าจู่ ๆ เข้าไม่ได้ ให้เช็ค `ipconfig` ใหม่อีกรอบ

---

## ส่วน B: ถ้าครูอยากเห็นว่าใช้ Coolify จริง ๆ

**ข้อเท็จจริงที่ต้องบอกตรง ๆ ก่อน:** Coolify ถูกออกแบบมาให้รันบน Linux
server เป็นหลัก การติดตั้งบน Windows ตรง ๆ **ไม่รองรับอย่างเป็นทางการ**
วิธีที่พอทำได้บน Windows คือติดตั้งผ่าน **WSL2** (Windows Subsystem for
Linux) ซึ่งมีความซับซ้อนกว่าส่วน A พอสมควร และเรื่องเน็ตเวิร์ก/กล้องก็ยังมี
ข้อจำกัดคล้ายเดิม (ต้องใช้ `camera_uploader.py` ช่วยเหมือนเดิม)

ถ้าเป้าหมายจริง ๆ คือ "มี server รันบนคอมตัวเอง ให้คนอื่นในวง WiFi เข้าดูได้"
**ส่วน A ก็ตอบโจทย์ครบแล้วโดยไม่ต้องใช้ Coolify เลย** ส่วน B นี้ทำเพิ่มเผื่อ
ครูเช็คว่าต้องเห็นหน้า Coolify Dashboard จริง ๆ

### B1) เปิดใช้งาน WSL2 + ติดตั้ง Ubuntu
เปิด PowerShell **แบบ Run as Administrator** แล้วรัน:

```powershell
wsl --install -d Ubuntu-22.04
```

รอติดตั้งเสร็จ เครื่องอาจขอรีสตาร์ท พอเปิดมาใหม่จะมีหน้าต่าง Ubuntu ขึ้นมา
ให้ตั้ง username/password ของ Linux (ตั้งอะไรก็ได้ จำไว้)

### B2) เปิด systemd ใน WSL2 (Coolify ต้องใช้)
ในหน้าต่าง Ubuntu (WSL2) ที่เปิดอยู่ พิมพ์:

```bash
sudo nano /etc/wsl.conf
```

ใส่เนื้อหานี้ลงไป (ถ้ามีเนื้อหาเดิมอยู่แล้วให้เพิ่มต่อท้าย):

```ini
[boot]
systemd=true
```

กด `Ctrl+O` แล้ว Enter เพื่อบันทึก, `Ctrl+X` เพื่อออก

กลับไปที่ PowerShell (ไม่ใช่หน้าต่าง Ubuntu) แล้วรัน:

```powershell
wsl --shutdown
```

รอ 10 วินาที แล้วเปิด Ubuntu ขึ้นมาใหม่ (หาใน Start menu พิมพ์ "Ubuntu")

### B3) ติดตั้ง Coolify
ในหน้าต่าง Ubuntu (WSL2) พิมพ์:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

รอจนติดตั้งเสร็จ (ใช้เวลาสักพัก)

### B4) เปิดหน้า Coolify Dashboard
เปิดเบราว์เซอร์บน Windows (เครื่องเดียวกัน) ไปที่:

```
http://localhost:8000
```

ควรเห็นหน้าตั้งค่า Coolify ครั้งแรก ทำตามขั้นตอนสร้างบัญชี admin ให้เสร็จ

### B5) Deploy โปรเจกต์ผ่าน Coolify
ทำตามขั้นตอนใน `DEPLOY-COOLIFY.md` (ไฟล์แนบมาให้อีกไฟล์) ตั้งแต่หัวข้อ "2)
เตรียมโค้ดขึ้น Git repository" เป็นต้นไปได้เลย ทุกอย่างเหมือนกัน (push
GitHub → สร้าง Application ใน Coolify → เลือก Dockerfile → ตั้ง port 5000 →
Deploy)

ส่วนกล้อง: หลัง deploy สำเร็จ ให้รัน `camera_uploader.py` บน Windows
(นอก WSL2 ก็ได้) แล้วชี้ `--server` ไปที่ URL ที่ Coolify ให้มา เช่น:

```powershell
python camera_uploader.py --server http://localhost:<port ที่ Coolify แจ้ง>
```

### B6) ให้เครื่องอื่นในวง WiFi เข้าถึง Coolify app ได้
ค่าเริ่มต้น WSL2 อาจไม่เปิดให้เครื่องอื่นในวง LAN เข้าถึง service ที่รันอยู่
ข้างในได้ตรง ๆ วิธีแก้ที่ง่ายที่สุด (Windows 11 เวอร์ชันใหม่): เปิดโหมด
mirrored networking — สร้าง/แก้ไฟล์ `C:\Users\<ชื่อคุณ>\.wslconfig` ใส่:

```ini
[wsl2]
networkingMode=mirrored
```

แล้ว `wsl --shutdown` แล้วเปิด Ubuntu ใหม่อีกครั้ง จากนั้นเครื่องอื่นในวง
WiFi จะเข้าได้ที่ `http://<IP คอมเซิร์ฟเวอร์ จาก A5>:<port>` เหมือนส่วน A7
(ถ้าใช้ Windows 10 หรือ Windows 11 รุ่นเก่าที่ไม่มี mirrored mode ต้องใช้
`netsh interface portproxy` ช่วย ซึ่งซับซ้อนกว่านี้ — ถ้าติดปัญหาตรงนี้บอก
ได้ เดี๋ยวช่วยทำ script ให้เพิ่ม)

---

## ส่วน C: ทำไมต้องมี `camera_uploader.py` แยกต่างหาก

โค้ดเดิม `cam_ai_server.py` เปิดกล้องด้วย `cv2.VideoCapture()` **จากข้างใน
container โดยตรง** ปัญหาคือ Docker บน Windows (ทั้ง Docker Desktop และ
Coolify-on-WSL2) รันอยู่ข้างใน WSL2 ซึ่ง **ไม่มี driver สำหรับอ่านภาพจาก USB
webcam ของเครื่อง Windows โดยตรง** (เป็นข้อจำกัดของ WSL2 เอง ไม่เกี่ยวกับ
โค้ดของโปรเจกต์นี้ และไม่มีวิธีแก้ง่าย ๆ ผ่าน config)

ผมเลยเพิ่มทางเลือกที่ 2 ให้ในโค้ด (`cam_ai_server.py`): ถ้า container เปิด
กล้องในเครื่องตัวเองไม่ได้ จะสลับไปรอรับภาพจาก endpoint ใหม่ `POST /frame`
แทนโดยอัตโนมัติ — `camera_uploader.py` ที่ให้มาคือสคริปต์เล็ก ๆ ที่รันตรงบน
Windows (เปิดกล้องได้ปกติเพราะไม่ผ่าน Docker/WSL2) แล้วส่งภาพเข้าไปทาง
endpoint นี้แทน ส่วน AI classify / เว็บ dashboard / เก็บ history ทุกอย่างยัง
ทำงานอยู่ใน Docker container เหมือนเดิมทั้งหมด ไม่ได้ย้ายออกมา

> ถ้าในอนาคตย้ายไปรันบนเครื่อง **Linux จริง** (ไม่ใช่ Windows) ที่มีเว็บแคม
> ต่ออยู่ ไม่ต้องใช้ `camera_uploader.py` เลย — เปิดคอมเมนต์ `devices:` ใน
> `docker-compose.yml` แล้ว container จะเห็นกล้องได้เองตรง ๆ ทันที
