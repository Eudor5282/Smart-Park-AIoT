"""
camera_uploader.py
===================
สคริปต์นี้รันบนเครื่อง Windows โดยตรง (นอก Docker) เพราะ container ที่รันบน
Windows มองไม่เห็นเว็บแคม USB ของโฮสต์โดยตรง (ข้อจำกัดของ Docker Desktop /
WSL2 บน Windows) สคริปต์นี้แค่จับภาพจากเว็บแคม แล้วส่งเข้าไปที่เซิร์ฟเวอร์ที่
รันอยู่ใน container ผ่าน HTTP (POST /frame) ส่วนงานหนัก (AI classify,
เว็บ dashboard, history) ยังทำงานอยู่ใน Docker เหมือนเดิมทั้งหมด

วิธีใช้:
  1. ติดตั้งไลบรารีที่ต้องใช้ (ครั้งเดียว):
       pip install opencv-python requests

  2. รัน docker compose up ให้ container ทำงานอยู่ก่อน (ดู DEPLOY-COOLIFY.md)

  3. เปิด Command Prompt / PowerShell อีกหน้าต่างนึง (แยกจากที่รัน Docker)
     แล้วรัน:
       python camera_uploader.py

     ถ้าเซิร์ฟเวอร์รันอยู่คนละเครื่อง/คนละพอร์ต ให้ระบุ --server ด้วย เช่น:
       python camera_uploader.py --server http://localhost:5000

  4. ปล่อยหน้าต่างนี้รันค้างไว้ตลอดเวลาที่ต้องการให้ระบบเห็นภาพจากกล้อง
     ปิดหน้าต่างนี้เมื่อไหร่ = กล้องหยุดส่งภาพเข้าเซิร์ฟเวอร์ (แต่เว็บ
     dashboard และเซนเซอร์ ultrasonic จาก Arduino ยังทำงานได้ปกติ)
"""

import argparse
import sys
import time

import cv2
import requests


def open_webcam(cam_index: int):
    backend_candidates = []
    if hasattr(cv2, "CAP_DSHOW"):
        backend_candidates.append(cv2.CAP_DSHOW)
    if hasattr(cv2, "CAP_MSMF"):
        backend_candidates.append(cv2.CAP_MSMF)
    backend_candidates.append(cv2.CAP_ANY)

    for backend in backend_candidates:
        cap = cv2.VideoCapture(cam_index, backend)
        if cap is not None and cap.isOpened():
            return cap
        if cap is not None:
            cap.release()
    return None


def main():
    parser = argparse.ArgumentParser(description="ส่งภาพจากเว็บแคมเข้า Docker server")
    parser.add_argument(
        "--server",
        default="http://localhost:5000",
        help="URL ของเซิร์ฟเวอร์ที่รันอยู่ใน Docker (ค่าเริ่มต้น: http://localhost:5000)",
    )
    parser.add_argument("--camera-index", type=int, default=0, help="ลำดับกล้อง (ปกติ 0)")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument(
        "--fps", type=float, default=10.0, help="ความถี่ในการส่งภาพต่อวินาที"
    )
    args = parser.parse_args()

    frame_url = f"{args.server.rstrip('/')}/frame"
    interval = 1.0 / max(args.fps, 0.1)

    print(f"[uploader] กำลังเปิดกล้อง index={args.camera_index} ...")
    cap = open_webcam(args.camera_index)
    if cap is None:
        print("[uploader] เปิดกล้องไม่สำเร็จ ตรวจสอบว่ามีเว็บแคมต่ออยู่และไม่มี", file=sys.stderr)
        print("[uploader] โปรแกรมอื่นแย่งใช้กล้องอยู่ (เช่น Zoom/Teams/Camera app)", file=sys.stderr)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    print(f"[uploader] เปิดกล้องสำเร็จ กำลังส่งภาพไปที่ {frame_url}")
    print("[uploader] กด Ctrl+C เพื่อหยุด")

    session = requests.Session()
    ok_count = 0
    fail_count = 0

    try:
        while True:
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                print("[uploader] อ่านเฟรมจากกล้องไม่สำเร็จ ลองใหม่...", file=sys.stderr)
                time.sleep(0.5)
                continue

            ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ok:
                continue

            try:
                resp = session.post(
                    frame_url,
                    data=buf.tobytes(),
                    headers={"Content-Type": "image/jpeg"},
                    timeout=2.0,
                )
                if resp.ok:
                    ok_count += 1
                else:
                    fail_count += 1
                    print(f"[uploader] เซิร์ฟเวอร์ตอบกลับผิดพลาด: HTTP {resp.status_code}")
            except requests.RequestException as e:
                fail_count += 1
                if fail_count % 20 == 1:
                    print(f"[uploader] ส่งภาพไม่สำเร็จ (เช็คว่า container รันอยู่ไหม): {e}")

            if (ok_count + fail_count) % 50 == 0:
                print(f"[uploader] ส่งสำเร็จ {ok_count} ครั้ง / ล้มเหลว {fail_count} ครั้ง")

            elapsed = time.time() - t0
            sleep_left = interval - elapsed
            if sleep_left > 0:
                time.sleep(sleep_left)
    except KeyboardInterrupt:
        print("\n[uploader] หยุดทำงาน")
    finally:
        cap.release()


if __name__ == "__main__":
    main()
