# คู่มือ Deploy โปรเจกต์ Smart Car Parking ด้วย Docker + Coolify

> ถ้าเครื่องที่จะใช้เป็น server เป็น **Windows** และต้องการให้เครื่องอื่นใน
> วง WiFi เดียวกันเข้าเว็บมาดูได้ ให้อ่าน **`START-HERE-WINDOWS.md`** ก่อน
> ไฟล์นั้นมีขั้นตอนเฉพาะสำหรับ Windows ที่ครบกว่า (Docker Desktop, firewall,
> หา IP, ตัวช่วยกล้อง camera_uploader.py) ไฟล์นี้ (`DEPLOY-COOLIFY.md`) เป็น
> คู่มือ Coolify แบบทั่วไป เหมาะกับกรณีมีเซิร์ฟเวอร์ Linux อยู่แล้ว

คู่มือนี้เขียนแบบละเอียดทุกขั้นตอน ทำตามได้เลยแม้ไม่เคยใช้ Docker มาก่อน

---

## 0) สิ่งที่ต้องรู้ก่อน (สำคัญมาก อ่านก่อนเริ่ม)

โค้ด `cam_ai_server.py` เปิดกล้องเว็บแคมด้วย `cv2.VideoCapture()` **จากเครื่อง
ที่รันโปรแกรมโดยตรง** ไม่ใช่จากเบราว์เซอร์ของผู้ใช้

ดังนั้น:

- **ถ้า Coolify รันอยู่บนคอมพิวเตอร์/เซิร์ฟเวอร์ที่มีเว็บแคมต่ออยู่จริง**
  (เช่น mini PC ที่ต่อกล้องไว้ข้างที่จอดรถจำลอง) → ใช้งานได้ปกติ ต้อง
  "ส่งอุปกรณ์กล้อง" เข้าไปใน container ด้วย (ทำตามขั้นตอนด้านล่าง)
- **ถ้า Coolify รันอยู่บนคลาวด์ VPS** (DigitalOcean, AWS, Hetzner ฯลฯ) ที่ไม่มี
  เว็บแคมต่ออยู่จริง → **ส่วนกล้อง AI จะใช้งานไม่ได้** เพราะ VPS ไม่มีกล้อง
  ให้เปิด แอปจะยังรันได้ปกติ (ไม่ crash) แต่หน้าเว็บจะขึ้นสถานะกล้องเป็น
  "camera: opened=false" ตลอด ส่วนระบบเซนเซอร์ ultrasonic จาก Arduino ยังทำงาน
  ได้ปกติ เพราะส่งข้อมูลผ่าน HTTP POST เข้ามาได้จากทุกที่

ถ้ายังไม่มีเซิร์ฟเวอร์ ให้เลือกเครื่องที่มีกล้องต่ออยู่ (เช่น PC/โน้ตบุ๊ก/มินิพีซี
ที่รัน Coolify เอง) จะได้ครบทุกฟีเจอร์ 100%

---

## 1) ทดสอบรันด้วย Docker ในเครื่องตัวเองก่อน (แนะนำให้ทำก่อนขึ้น Coolify)

ติดตั้ง Docker Desktop ก่อน (ถ้ายังไม่มี): https://www.docker.com/products/docker-desktop/

เปิด Terminal / Command Prompt ไปที่โฟลเดอร์โปรเจกต์ (โฟลเดอร์ที่มี
`Dockerfile` อยู่) แล้วรัน:

```bash
docker compose up --build
```

รอสักครู่ (รอบแรกจะช้าเพราะต้องโหลด TensorFlow ~600MB) พอเห็น log ประมาณ

```
[WEB] WEB_ROOT = /app
[WEB] เจอไฟล์ index.html ไหม: True
Listening at: http://0.0.0.0:5000
```

เปิดเบราว์เซอร์ไปที่ `http://localhost:5000` ควรเห็นหน้าเว็บ

ถ้าเครื่องที่รันมีเว็บแคมและอยากทดสอบกล้องจริง ให้เปิดคอมเมนต์ส่วน
`devices:` ใน `docker-compose.yml` ก่อน (ดูรายละเอียดในไฟล์นั้น — Windows/Mac
ผ่าน Docker Desktop จะพาสกล้องเข้า container ยากกว่า Linux ตรง ๆ แนะนำ
ทดสอบกล้องบนเครื่อง Linux จริงถ้าเป็นไปได้)

กด `Ctrl+C` เพื่อหยุด

---

## 2) เตรียมโค้ดขึ้น Git repository (GitHub/GitLab)

Coolify ดึงโค้ดจาก Git repo มา build ให้เอง ต้องมี repo ก่อน

1. สร้าง repo ใหม่บน GitHub (เช่น `smart-car-parking`)
2. ในโฟลเดอร์โปรเจกต์ รันคำสั่ง (ครั้งแรกเท่านั้น):

```bash
git init
git add .
git commit -m "Initial commit: Docker setup for Coolify"
git branch -M main
git remote add origin https://github.com/<username>/smart-car-parking.git
git push -u origin main
```

> หมายเหตุ: ไฟล์ `Model/keras_model.h5` มีขนาดพอสมควร (~2.4MB) ปกติ push
> ขึ้น GitHub ได้สบาย ไม่ต้องใช้ Git LFS

---

## 3) สร้าง Application ใหม่ใน Coolify

1. เข้า Coolify Dashboard → เลือก Project ที่จะใช้ (หรือสร้างใหม่)
2. กด **+ New** → **Resource** → **Application**
3. เลือกวิธีเชื่อม: **Git Source** → เชื่อม GitHub account (ถ้ายังไม่เชื่อม)
   แล้วเลือก repository `smart-car-parking` ที่เพิ่ง push ไป
4. เลือก Branch: `main`
5. **Build Pack**: เลือก **Dockerfile** (Coolify จะเจอ `Dockerfile` ใน repo
   อัตโนมัติแล้วใช้ build ให้เอง ไม่ต้องเลือก Nixpacks)
6. **Port**: ใส่ `5000` (ตรงกับ `EXPOSE 5000` ใน Dockerfile และพอร์ตที่
   gunicorn ฟังอยู่)

---

## 4) ตั้งค่า Volume (กันข้อมูลประวัติการจอดหาย)

โปรแกรมเขียนไฟล์ `Model/history.jsonl` เก็บประวัติการจอดรถ (ใช้ทำกราฟ) ถ้าไม่
ตั้ง volume ไว้ ทุกครั้งที่ deploy ใหม่หรือ container รีสตาร์ท ข้อมูลนี้จะ
หายหมด

ใน Coolify → หน้า Application → แท็บ **Storages** → **+ Add**:

| Field | ค่าที่ใส่ |
|---|---|
| Name | `parking-history` |
| Destination Path (ใน container) | `/app/Model` |

บันทึกไว้ก่อน deploy ครั้งแรก

---

## 5) ตั้งค่าอุปกรณ์กล้อง (เฉพาะกรณีเซิร์ฟเวอร์มีเว็บแคมต่ออยู่จริง)

ถ้าเซิร์ฟเวอร์ที่รัน Coolify มี USB webcam ต่ออยู่จริง (Linux host):

1. บนเครื่องโฮสต์ รันคำสั่งเช็คว่ากล้องอยู่ที่ device ไหน:
   ```bash
   ls /dev/video*
   ```
   ปกติจะเห็น `/dev/video0`
2. ใน Coolify ปัจจุบัน (เวอร์ชันส่วนใหญ่) การส่ง `--device` ผ่านหน้า UI
   โดยตรงยังไม่รองรับเต็มรูปแบบ วิธีที่ชัวร์ที่สุดคือเปลี่ยนวิธี deploy จาก
   "Dockerfile" เป็น **Docker Compose** แทน แล้วใช้ไฟล์
   `docker-compose.yml` ที่แนบมาให้ (ซึ่งมีส่วน `devices:` เตรียมไว้แล้ว
   แค่เอา `#` ออก):
   - ใน Coolify: New Resource → Application → เลือก **Docker Compose**
     แทน Dockerfile แล้วชี้ไปที่ `docker-compose.yml` ใน repo
3. ถ้าไม่มีเว็บแคมต่ออยู่ ข้ามขั้นตอนนี้ไปได้เลย แอปจะรันได้ปกติแค่ไม่มีภาพ
   จากกล้อง

---

## 6) Deploy

กดปุ่ม **Deploy** ใน Coolify รอ build (รอบแรกช้าหน่อยเพราะโหลด TensorFlow
~600MB) เช็ค log ใน Coolify ว่าขึ้น

```
Listening at: http://0.0.0.0:5000
```

ก็คือสำเร็จ จากนั้นตั้งโดเมน (Coolify จะมี URL ให้อัตโนมัติ หรือใส่โดเมนของ
ตัวเองในแท็บ **Domains** ก็ได้ Coolify จัดการ HTTPS ให้อัตโนมัติผ่าน Let's
Encrypt)

---

## 7) ตั้งค่าฝั่ง Arduino (บอร์ด ESP32/UNO R4 WiFi) ให้ยิงข้อมูลมาที่เซิร์ฟเวอร์ใหม่

ไฟล์ `SmartCarParking n.ino` เดิมรัน HTTP server อยู่ *บน*บอร์ด Arduino เอง
(ไม่ได้ยิงออกไปหาเซิร์ฟเวอร์) ถ้าต้องการให้บอร์ดส่งข้อมูล ultrasonic ไปที่
เซิร์ฟเวอร์ที่ deploy บน Coolify แทน (endpoint `POST /ultrasonic`) จะต้อง
แก้โค้ด `.ino` เพิ่มส่วนยิง HTTP request ออกไปที่โดเมนของ Coolify — ถ้าต้องการ
ให้ผมช่วยแก้ส่วนนี้ด้วย บอกได้เลย เดี๋ยวทำให้อีกไฟล์นึงแยกต่างหาก

---

## 8) แก้ปัญหาที่เจอบ่อย

| อาการ | สาเหตุที่เป็นไปได้ | วิธีแก้ |
|---|---|---|
| Build ค้างนาน/timeout | โหลด TensorFlow ~600MB ครั้งแรก | รอให้จบ (ปกติ 3-8 นาทีขึ้นกับความเร็วเน็ตเซิร์ฟเวอร์) |
| หน้าเว็บขึ้นแต่ไม่มีภาพกล้อง | เซิร์ฟเวอร์ไม่มีเว็บแคม หรือยังไม่ได้ pass device เข้า container | ดูข้อ 5 หรือถ้าเป็น VPS คลาวด์ คือใช้กล้องไม่ได้โดยธรรมชาติของ VPS |
| ประวัติการจอด (กราฟ) หายทุกครั้งที่ deploy ใหม่ | ยังไม่ได้ตั้ง Volume | ดูข้อ 4 |
| `ImportError: libGL.so.1` ตอน build/run | ขาดไลบรารีระบบ | Dockerfile ที่แนบมาติดตั้ง `libgl1` ให้แล้ว ถ้ายังเจอ ลองสั่ง Rebuild ใหม่แบบไม่ใช้ cache ใน Coolify |
| กล้องเปิดได้ในเครื่อง Windows ตอน dev แต่ใน container เปิดไม่ได้ | container เป็น Linux เสมอ (แม้โฮสต์เป็น Windows) จึงใช้ backend `CAP_DSHOW`/`CAP_MSMF` ของ Windows ไม่ได้ | โค้ดจัดการเรื่องนี้ให้แล้ว (เช็ค `hasattr` ก่อนใช้ แล้ว fallback ไป `CAP_ANY`) แค่ต้องรันบนโฮสต์ Linux ที่มีกล้องจริงต่ออยู่ |

---

## สรุปไฟล์ที่เพิ่มเข้ามาให้ในโปรเจกต์

- `Dockerfile` — สั่ง build image
- `.dockerignore` — กันไฟล์ขยะ (venv, .git, __pycache__) หลุดเข้า image
- `docker-compose.yml` — ใช้ทดสอบในเครื่อง + ใช้เป็น deploy mode ใน Coolify ถ้าต้องพาสกล้องเข้า container
- `requirements.txt` — รายการไลบรารี Python ที่ต้องติดตั้ง
- `camera_uploader.py` — สคริปต์รันนอก Docker บนเครื่อง Windows เพื่อส่งภาพเว็บแคมเข้า container (ดูเหตุผลในข้อ 5 และ `START-HERE-WINDOWS.md`)
- `START-HERE-WINDOWS.md` — คู่มือเฉพาะสำหรับใช้คอม Windows เป็น server ให้เครื่องอื่นในวง WiFi เข้าดูได้
- แก้ไข `cam_ui_inject.js` — เดิม hardcode URL เป็น `127.0.0.1:5000` ซึ่งพังแน่นอนเมื่อ deploy จริงผ่าน reverse proxy ของ Coolify แก้ให้ใช้ URL เดียวกับหน้าเว็บเสมอ (same-origin)
- แก้ไข `cam_ai_server.py` — เพิ่ม endpoint `POST /frame` และโหมด external-frame fallback อัตโนมัติ เมื่อ container เปิดกล้องในเครื่องเองไม่ได้ (กรณี Windows/WSL2)
