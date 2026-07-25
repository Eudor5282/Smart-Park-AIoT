@echo off
REM Smart Car Parking - รันแบบ native บน Windows (ไม่ใช้ Docker)
REM เหตุผล: Docker Desktop บน Windows เข้าถึงกล้อง USB ของเครื่องโดยตรงไม่ได้
REM สคริปต์นี้จะสร้าง virtual environment ให้อัตโนมัติ (รันครั้งแรกจะช้าหน่อย
REM เพราะต้องโหลด TensorFlow ~ครั้งเดียว รันครั้งต่อไปจะเร็วขึ้นมาก)

cd /d "%~dp0"

if not exist venv (
    echo [SETUP] กำลังสร้าง virtual environment ครั้งแรก...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [SETUP] กำลังติดตั้ง/อัปเดตไลบรารีที่จำเป็น...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo.
echo [RUN] เปิดเซิร์ฟเวอร์ Smart Car Parking ที่พอร์ต 5000
echo [RUN] เครื่องคนอื่นในวง Wi-Fi/LAN เดียวกัน เปิดเบราว์เซอร์ไปที่ http://IP-เครื่องนี้:5000
echo [RUN] (ดู IP เครื่องนี้ด้วยคำสั่ง: ipconfig แล้วดูช่อง IPv4 Address)
echo [RUN] กด Ctrl+C เพื่อปิดเซิร์ฟเวอร์
echo.

python cam_ai_server.py

pause
