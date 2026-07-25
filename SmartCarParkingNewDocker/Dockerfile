# Smart Car Parking - Docker image
# หมายเหตุ: image นี้ตั้งใจให้รันบน Linux host (native Linux หรือ Raspberry Pi)
# เพราะเป็น OS เดียวที่ Docker เข้าถึงกล้อง USB ของเครื่องได้จริงผ่าน --device
# ถ้า host เป็น Windows/Mac ให้ดู README.md หัวข้อ "รันแบบไม่ใช้ Docker (Windows/Mac)"

FROM python:3.10-slim

# ไลบรารีระบบที่ OpenCV และ TensorFlow ต้องใช้ (แม้ใช้ opencv-python-headless
# ก็ยังต้องพึ่ง libgl1/libglib สำหรับ codec บางตัว)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ติดตั้ง dependencies ก่อน แยก layer เพื่อให้ docker cache ไว้ (build รอบถัดไปเร็วขึ้น
# ถ้าไม่ได้แก้ requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกซอร์สทั้งหมด (เว้นสิ่งที่อยู่ใน .dockerignore เช่น __pycache__)
COPY . .

ENV PYTHONUNBUFFERED=1
# ปิด log กวนใจของ TensorFlow (0=all,1=info,2=warning,3=error)
ENV TF_CPP_MIN_LOG_LEVEL=2

EXPOSE 5000

# healthcheck: เช็คว่า Flask ตอบ / ได้ไหม (ไม่ได้เช็คว่ากล้องเปิดสำเร็จหรือไม่ ดู
# สถานะกล้องจริงได้ที่ /video -> preds.camera.opened)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/')" || exit 1

CMD ["python", "cam_ai_server.py"]
