#!/usr/bin/env bash
# Smart Car Parking - รันแบบ native บน Mac (หรือ Linux ที่ไม่อยากใช้ Docker)
# เหตุผล: Docker Desktop บน Mac เข้าถึงกล้อง USB ของเครื่องโดยตรงไม่ได้
set -e

cd "$(dirname "$0")"

if [ ! -d venv ]; then
  echo "[SETUP] กำลังสร้าง virtual environment ครั้งแรก..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "[SETUP] กำลังติดตั้ง/อัปเดตไลบรารีที่จำเป็น..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

IP_ADDR=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n1)

echo ""
echo "[RUN] เปิดเซิร์ฟเวอร์ Smart Car Parking ที่พอร์ต 5000"
echo "[RUN] เครื่องคนอื่นในวง Wi-Fi/LAN เดียวกัน เปิดเบราว์เซอร์ไปที่ http://${IP_ADDR:-<IP เครื่องนี้>}:5000"
echo "[RUN] กด Ctrl+C เพื่อปิดเซิร์ฟเวอร์"
echo ""

python cam_ai_server.py
