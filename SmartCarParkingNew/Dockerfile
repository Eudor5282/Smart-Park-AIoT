# =========================================================
# Dockerfile - Smart Car Parking (Flask + OpenCV + TensorFlow)
# =========================================================
# ใช้ python:3.10-slim เพราะโปรเจกต์นี้ dev มาด้วย Python 3.10
# (ดูได้จากไฟล์ __pycache__/*.cpython-310.pyc ที่แถมมาในโปรเจกต์)
FROM python:3.10-slim

# ป้องกัน python เขียนไฟล์ .pyc และให้ print() ออก log ทันที (ไม่ถูก buffer)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# ไลบรารีระบบที่ opencv-python-headless ต้องใช้ตอน runtime
# (libgl1/libglib2.0-0 จำเป็นแม้จะใช้ opencv "headless" ก็ตาม เพราะ cv2
# ยัง import บาง symbol จาก libGL / glib อยู่ ถ้าไม่มีจะ import cv2 ไม่ผ่าน)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง python dependencies ก่อน แยก layer จากโค้ด เพื่อให้ Docker cache
# layer นี้ไว้ได้ (build รอบถัดไปจะไม่ต้องโหลด/ติดตั้ง tensorflow ใหม่ทุกครั้ง
# ถ้า requirements.txt ไม่เปลี่ยน)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดโปรเจกต์ทั้งหมดเข้า image
COPY . .

# โฟลเดอร์ Model/ ใช้เก็บ history.jsonl ที่เขียนทับตลอดเวลาตอน runtime
# ต้องแน่ใจว่ามีอยู่ใน image เสมอ (เผื่อกรณี .dockerignore กรองไฟล์บางไฟล์ออก)
RUN mkdir -p /app/Model

# Flask/Gunicorn ฟังที่ port 5000 ภายใน container
# (Coolify จะ map port นี้ออกไปให้เองผ่าน reverse proxy ของมัน)
EXPOSE 5000

# ใช้ gunicorn แทน `python cam_ai_server.py` โดยตรง เพราะ Flask dev server
# (app.run) ไม่เหมาะกับ production: เธรดเดียว/ไม่มี auto-restart เวลา error
# --workers 1 : จำเป็นต้องมี worker เดียว เพราะโมเดล AI /กล้อง/ตัวแปร state
# ทั้งหมดเป็น in-memory (global variable) ถ้ามีหลาย worker แต่ละ process
# จะเปิดกล้อง/โหลดโมเดลแยกกันคนละชุด แล้วข้อมูลจะไม่ตรงกัน
# --threads 4 : ให้รับหลาย request พร้อมกันได้ภายใน worker เดียว (เช่น
# /video, /ultrasonic, /history และเสิร์ฟไฟล์หน้าเว็บพร้อมกัน)
# --timeout 120 : กันไม่ให้ gunicorn ฆ่า worker ทิ้งระหว่างโหลดโมเดล TensorFlow
# ตอนเริ่มต้น ซึ่งอาจใช้เวลาหลายวินาที
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "cam_ai_server:app"]
