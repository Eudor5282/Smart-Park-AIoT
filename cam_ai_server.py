import base64
from dataclasses import dataclass
import json
import os
import threading
import time
from typing import Dict, Optional, Tuple

import cv2
from flask import Flask, jsonify, make_response, request, send_from_directory
import numpy as np

app = Flask(__name__)

# โฟลเดอร์ที่เก็บไฟล์หน้าเว็บ (index.html, script.js, cam_ui_inject.js, style.css)
# ตั้งเป็นโฟลเดอร์เดียวกับที่ไฟล์ .py นี้อยู่ เพื่อให้ Flask เสิร์ฟหน้าเว็บเองได้เลย
# ไม่ต้องพึ่ง VS Code Live Server อีกต่อไป (Live Server สั่ง reload หน้าเว็บทุก
# ครั้งที่มีไฟล์ในโปรเจกต์เปลี่ยน ซึ่งชนกับที่โปรแกรมนี้เขียนไฟล์ลง Model/ ตลอดเวลา)
WEB_ROOT = os.path.dirname(os.path.abspath(__file__))

# -----------------------
# Config
# -----------------------
MODEL_PATH = "Model/keras_model.h5"
LABELS_PATH = "Model/labels.txt"

CAM_INDEX = int(0)
CAP_WIDTH = 640
CAP_HEIGHT = 480

# คีย์เวิร์ดสำหรับระบุคลาส "ไม่ใช่รถ" (เช็คก่อนคลาส "รถ" เสมอ)
# สำคัญ: ต้องเช็ค "notcar" ก่อน เพราะคำว่า "car" ซ่อนอยู่ในคำว่า "notcar" ด้วย
# (not + car) ถ้าเช็คคลาสรถก่อน จะจับ "NotCar" ผิดเป็น "รถ" ทันที
NOT_CAR_KEYWORDS = (
    "notcar", "not_car", "not car",
    "hand", "มือ", "other", "อื่น", "object", "obstacle",
)

# คีย์เวิร์ดสำหรับระบุว่าเป็น "รถ"
TOY_CAR_KEYWORDS = ("car", "รถ", "vehicle")

# คีย์เวิร์ดสำหรับระบุคลาส "ว่าง" (เผื่อโมเดลรุ่นอื่นมี class นี้ด้วยในอนาคต
# โมเดลปัจจุบันมีแค่ 2 class คือ Car / NotCar ไม่ได้ใช้ค่านี้ แต่เก็บไว้เผื่ออนาคต)
EMPTY_KEYWORDS = ("empty", "ว่าง", "none", "background")

# เกณฑ์ความมั่นใจขั้นต่ำที่ต้องผ่านถึงจะยอมรับว่าเป็น "รถ"
TOY_CAR_CONF_THRESHOLD = float(0.60)

# ต้องเจอผลเดิมติดต่อกันกี่เฟรมก่อนจะ "ยืนยัน" สถานะ (ลด false positive จากเฟรมเดียว)
CONFIRM_FRAMES = 3

ZONE_IDS = ("P1", "P2", "P3", "P4")

ZONE_BOUNDS = {
    "P4": (0.00, 0.25),
    "P3": (0.25, 0.50),
    "P2": (0.50, 0.75),
    "P1": (0.75, 1.00),
}

ZONE_CROP_PADDING_RATIO = 0.12
P1_EXTRA_LEFT_PADDING_RATIO = 0.08

DEBUG_CAMERA_OPEN_LOG = True


@dataclass
class ZonePred:
  status: str
  confidence: float


# =========================================================
# โหลดโมเดล Teachable Machine (รองรับความเข้ากันได้หลายเวอร์ชันของ Keras)
# =========================================================

def _sanitize_model_config(config):
  if isinstance(config, dict):
    sanitized = {}
    for key, value in config.items():
      if key == "groups":
        continue
      if isinstance(value, (dict, list)):
        sanitized[key] = _sanitize_model_config(value)
      else:
        sanitized[key] = value
    return sanitized
  if isinstance(config, list):
    return [_sanitize_model_config(item) for item in config]
  return config


def _load_model_with_compat(model_path: str):
  import h5py
  import tensorflow as tf
  from tensorflow import keras

  tf_keras_error_text = ""
  try:
    import tf_keras
    return tf_keras.models.load_model(model_path, compile=False)
  except Exception as tf_keras_error:
    tf_keras_error_text = str(tf_keras_error)

  try:
    return keras.models.load_model(model_path, compile=False)
  except Exception as first_error:
    try:
      with h5py.File(model_path, "r") as handle:
        if "model_config" in handle.attrs:
          config_bytes = handle.attrs["model_config"]
          if isinstance(config_bytes, bytes):
            config_bytes = config_bytes.decode("utf-8")
          model_config = json.loads(config_bytes)
        else:
          raise ValueError("model_config attribute not found")

      sanitized_config = _sanitize_model_config(model_config)
      if hasattr(keras.models, "model_from_config"):
        model = keras.models.model_from_config(sanitized_config)
      else:
        model = keras.models.model_from_json(json.dumps(sanitized_config))
      model.load_weights(model_path)
      return model
    except Exception as second_error:

      class CompatDepthwiseConv2D(tf.keras.layers.DepthwiseConv2D):
        def __init__(self, *args, **kwargs):
          kwargs.pop("groups", None)
          super().__init__(*args, **kwargs)

        @classmethod
        def from_config(cls, config):
          config.pop("groups", None)
          return cls(**config)

      class CompatSeparableConv2D(tf.keras.layers.SeparableConv2D):
        def __init__(self, *args, **kwargs):
          kwargs.pop("groups", None)
          super().__init__(*args, **kwargs)

        @classmethod
        def from_config(cls, config):
          config.pop("groups", None)
          return cls(**config)

      custom_objects = {
          "DepthwiseConv2D": CompatDepthwiseConv2D,
          "SeparableConv2D": CompatSeparableConv2D,
      }
      try:
        return keras.models.load_model(
            model_path, compile=False, custom_objects=custom_objects
        )
      except Exception as third_error:
        raise RuntimeError(
            f"Unable to load model: {tf_keras_error_text}\n{first_error}\n{second_error}\n{third_error}"
        ) from third_error


class SimpleTeachableClassifier:
  def __init__(self, model_path: str, labels_path: str):
    if not os.path.exists(model_path):
      raise FileNotFoundError(f"ไม่พบโมเดล: {model_path}")
    if not os.path.exists(labels_path):
      raise FileNotFoundError(f"ไม่พบ labels: {labels_path}")

    self.model = _load_model_with_compat(model_path)
    self.class_names = self._load_labels(labels_path)

  def _load_labels(self, labels_path: str):
    class_names = []
    with open(labels_path, "r", encoding="utf-8") as f:
      for line in f:
        line = line.strip()
        if not line:
          continue
        parts = line.split(" ", 1)
        class_names.append(parts[1] if len(parts) == 2 else parts[0])
    return class_names

  def predict(self, frame: np.ndarray) -> Tuple[str, float, np.ndarray]:
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = cv2.resize(rgb_frame, (224, 224))
    img = img.astype(np.float32)
    img = (img / 127.5) - 1.0
    img = np.expand_dims(img, axis=0)

    probs = self.model.predict(img, verbose=0)[0]
    best_idx = int(np.argmax(probs))
    return self.class_names[best_idx], float(probs[best_idx]), probs


class FallbackClassifier:
  def __init__(self, reason: str):
    self.reason = reason

  def predict(self, frame: np.ndarray) -> Tuple[str, float, np.ndarray]:
    return "fallback", 0.0, np.zeros((1, 1), dtype=np.float32)


# =========================================================
# สถานะกล้อง / ultrasonic / ความเสถียรของสถานะแต่ละช่อง
# =========================================================

class CamState:
  def __init__(self):
    self.lock = threading.Lock()
    self.last_payload: Dict = self._make_camera_payload(
        opened=False, reason="initializing"
    )

  def _make_camera_payload(self, opened: bool, reason: str):
    return {
        "img": None,
        "preds": {
            "fps": 0,
            "ts": time.time(),
            "camera": {"opened": opened, "reason": reason},
            "zones": {
                "P1": {"status": "-", "confidence": 0, "decision": "UNKNOWN"},
                "P2": {"status": "-", "confidence": 0, "decision": "UNKNOWN"},
                "P3": {"status": "-", "confidence": 0, "decision": "UNKNOWN"},
                "P4": {"status": "-", "confidence": 0, "decision": "UNKNOWN"},
            },
        },
    }


cam_state = CamState()


class UltrasonicState:
  def __init__(self):
    self.lock = threading.Lock()
    self.slots = {zid: "unknown" for zid in ZONE_IDS}
    self.ts = 0.0

  def update(self, slots: Dict[str, str]):
    normalized = {}
    for zid in ZONE_IDS:
      value = str(slots.get(zid, "unknown")).strip().lower()
      if value in ("occupied", "busy", "not_empty", "1", "true"):
        normalized[zid] = "occupied"
      elif value in ("empty", "available", "0", "false"):
        normalized[zid] = "empty"
      else:
        normalized[zid] = "unknown"

    with self.lock:
      self.slots = normalized
      self.ts = time.time()

  def snapshot(self) -> Dict[str, str]:
    with self.lock:
      return dict(self.slots)


ultrasonic_state = UltrasonicState()


class ZoneStabilizer:
  """เก็บสถานะล่าสุดของแต่ละโซน และต้องเห็นผลเดิมซ้ำกันติดต่อกัน
  CONFIRM_FRAMES ครั้งก่อนจะเปลี่ยนสถานะจริง เพื่อลดการกระพริบ/ทายผิด
  แบบเฟรมเดียว"""

  def __init__(self):
    self.lock = threading.Lock()
    self.state: Dict[str, Dict] = {
        zid: {"confirmed": "Empty", "pending": None, "count": 0}
        for zid in ZONE_IDS
    }

  def reset_zone(self, zid: str, status: str = "Empty"):
    with self.lock:
      self.state[zid] = {"confirmed": status, "pending": None, "count": 0}

  def update(self, zid: str, raw_status: str) -> str:
    with self.lock:
      s = self.state[zid]
      if raw_status == s["confirmed"]:
        s["pending"] = None
        s["count"] = 0
        return s["confirmed"]

      if s["pending"] != raw_status:
        s["pending"] = raw_status
        s["count"] = 1
      else:
        s["count"] += 1

      if s["count"] >= CONFIRM_FRAMES:
        s["confirmed"] = raw_status
        s["pending"] = None
        s["count"] = 0

      return s["confirmed"]


zone_stabilizer = ZoneStabilizer()


# =========================================================
# บันทึกเวลาจอด (session tracking) + ประวัติสำหรับทำกราฟ
# =========================================================

HISTORY_LOG_PATH = "Model/history.jsonl"
HISTORY_READ_LIMIT = 5000


class SessionTracker:
  """ตรวจจับจังหวะที่ช่องเปลี่ยนจาก 'ไม่มีรถ' -> 'มีรถ' (เริ่มจอด) และ
  'มีรถ' -> 'ไม่มีรถ' (ออกจากช่อง) แล้วบันทึกแต่ละรอบการจอดเป็น 1 บรรทัด
  ใน log file (jsonl) เพื่อเอาไปทำกราฟทีหลัง"""

  def __init__(self, log_path: str):
    self.lock = threading.Lock()
    self.log_path = log_path
    self.active_start: Dict[str, Optional[float]] = {zid: None for zid in ZONE_IDS}
    self.last_status: Dict[str, str] = {zid: "Empty" for zid in ZONE_IDS}
    # ไม่บันทึกรอบการจอดที่สั้นกว่านี้ลง log (กันสัญญาณรบกวน/กระพริบ ทำให้
    # ไฟล์ history โตเร็วผิดปกติ)
    self.min_duration_sec = 3.0
    log_dir = os.path.dirname(log_path)
    if log_dir:
      os.makedirs(log_dir, exist_ok=True)

  def update(self, zid: str, status: str, now: float):
    with self.lock:
      prev = self.last_status.get(zid, "Empty")

      if status == "Occupied" and prev != "Occupied":
        self.active_start[zid] = now

      elif status != "Occupied" and prev == "Occupied":
        start = self.active_start.get(zid)
        if start is not None and (now - start) >= self.min_duration_sec:
          self._append_record(zid, start, now)
        self.active_start[zid] = None

      self.last_status[zid] = status

  def _append_record(self, zid: str, start: float, end: float):
    record = {
        "zone": zid,
        "start_ts": start,
        "end_ts": end,
        "duration_sec": max(0.0, end - start),
    }
    try:
      with open(self.log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    except Exception:
      pass

  def get_active_start(self, zid: str) -> Optional[float]:
    with self.lock:
      return self.active_start.get(zid)

  def read_history(self, limit: int = HISTORY_READ_LIMIT) -> list:
    records = []
    if not os.path.exists(self.log_path):
      return records
    try:
      with open(self.log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
      for line in lines[-limit:]:
        line = line.strip()
        if not line:
          continue
        try:
          records.append(json.loads(line))
        except Exception:
          continue
    except Exception:
      pass
    return records


session_tracker = SessionTracker(HISTORY_LOG_PATH)

# เก็บเฟรมล่าสุดจากกล้องไว้ (ปัจจุบันไม่มี endpoint ใดใช้แล้ว แต่เก็บไว้เผื่อ
# ต้องการต่อยอด debug ในอนาคต)
latest_frame_lock = threading.Lock()
latest_frame: Optional[np.ndarray] = None


def frame_to_jpeg_base64(frame: np.ndarray, quality: int = 80) -> str:
  encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
  ok, buf = cv2.imencode(".jpg", frame, encode_param)
  if not ok:
    return ""
  return base64.b64encode(buf).decode("utf-8")


def _zone_crop(frame: np.ndarray, zone_id: str) -> np.ndarray:
  h, w = frame.shape[:2]
  start_ratio, end_ratio = ZONE_BOUNDS[zone_id]
  pad = ZONE_CROP_PADDING_RATIO + (
      P1_EXTRA_LEFT_PADDING_RATIO if zone_id == "P1" else 0.0
  )
  start_ratio = max(0.0, start_ratio - pad)
  end_ratio = min(1.0, end_ratio + ZONE_CROP_PADDING_RATIO)
  x1 = int(start_ratio * w)
  x2 = int(end_ratio * w)
  if x1 == x2:
    x2 = x1 + 1
  return frame[:, x1:x2]


def _draw_zone_overlay(
    frame: np.ndarray, active_slots: Dict[str, str]
) -> np.ndarray:
  view = frame.copy()
  h, w = view.shape[:2]

  for zid in ("P4", "P3", "P2", "P1"):
    start_ratio, end_ratio = ZONE_BOUNDS[zid]
    x1 = int(start_ratio * w)
    x2 = int(end_ratio * w)
    state = active_slots.get(zid, "unknown")
    color = (0, 210, 255) if state == "occupied" else (80, 80, 80)
    cv2.rectangle(view, (x1, 0), (x2 - 1, h - 1), color, 2)
    cv2.putText(
        view,
        zid,
        (x1 + 12, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        color,
        2,
        cv2.LINE_AA,
    )

  return view


# =========================================================
# ตัวตัดสินหลัก: AI classifier (Teachable Machine, 2 class: Car / NotCar)
# =========================================================

def _classify_crop(classifier, crop: np.ndarray) -> ZonePred:
  """ส่งภาพครอปเข้าโมเดล AI แล้วตัดสินว่าเป็น Occupied (รถ) หรือ NotCar
  (ไม่ใช่รถ) เช็คคำว่า 'ไม่ใช่รถ' ก่อนเสมอ เพื่อกันปัญหาคำว่า 'car' ที่ซ่อน
  อยู่ในคำว่า 'notcar' (not + car) ถูกจับผิดเป็นคลาสรถ"""
  if classifier is None:
    return ZonePred(status="NoClassifier", confidence=0.0)

  best_name, best_conf, probs = classifier.predict(crop)
  label_lower = str(best_name).lower()

  is_explicit_not_car = any(keyword in label_lower for keyword in NOT_CAR_KEYWORDS)
  is_explicit_empty = any(keyword in label_lower for keyword in EMPTY_KEYWORDS)
  is_toy_car = any(keyword in label_lower for keyword in TOY_CAR_KEYWORDS)

  if is_explicit_not_car or is_explicit_empty:
    return ZonePred(status="NotCar", confidence=best_conf)

  if is_toy_car and best_conf >= TOY_CAR_CONF_THRESHOLD:
    return ZonePred(status="Occupied", confidence=best_conf)

  return ZonePred(status="NotCar", confidence=best_conf)


def classify_frame_into_zones(
    classifier, frame: np.ndarray, active_slots: Dict[str, str]
) -> Dict[str, ZonePred]:
  zones: Dict[str, ZonePred] = {}

  for zid in ZONE_IDS:
    if active_slots.get(zid) != "occupied":
      zones[zid] = ZonePred(status="Empty", confidence=0.0)
      zone_stabilizer.reset_zone(zid, "Empty")
      continue

    crop = _zone_crop(frame, zid)
    raw_pred = _classify_crop(classifier, crop)
    confirmed_status = zone_stabilizer.update(zid, raw_pred.status)
    zones[zid] = ZonePred(status=confirmed_status, confidence=raw_pred.confidence)

  return zones


def open_camera_multi_try():
  backend_list = []
  if hasattr(cv2, "CAP_DSHOW"):
    backend_list.append(("DSHOW", cv2.CAP_DSHOW))
  if hasattr(cv2, "CAP_MSMF"):
    backend_list.append(("MSMF", cv2.CAP_MSMF))
  backend_list.append(("ANY", cv2.CAP_ANY))

  indices = [CAM_INDEX, 0, 1, 2]

  for idx in indices:
    for backend_name, backend in backend_list:
      cap = None
      try:
        cap = cv2.VideoCapture(idx, backend)
        if cap is not None and cap.isOpened():
          if DEBUG_CAMERA_OPEN_LOG:
            print(f"[CAM] opened: index={idx} backend={backend_name}")
          return cap
      except Exception:
        pass
      finally:
        try:
          if cap is not None and not cap.isOpened():
            cap.release()
        except Exception:
          pass
  return None


def camera_worker():
  global latest_frame

  cap = open_camera_multi_try()
  if cap is None:
    if DEBUG_CAMERA_OPEN_LOG:
      print("[CAM] open failed: could not open any backend/index")
    with cam_state.lock:
      cam_state.last_payload = cam_state._make_camera_payload(
          opened=False, reason="open failed"
      )
    return

  cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)

  with cam_state.lock:
    cam_state.last_payload = cam_state._make_camera_payload(
        opened=True, reason="camera connected"
    )

  classifier = None
  classifier_reason = ""
  try:
    classifier = SimpleTeachableClassifier(MODEL_PATH, LABELS_PATH)
    print(f"[AI] โหลดโมเดลสำเร็จ classes = {classifier.class_names}")
  except Exception as e:
    classifier_reason = str(e)
    classifier = FallbackClassifier(classifier_reason)
    print(f"[AI] โหลดโมเดลไม่สำเร็จ: {classifier_reason}")

  # นับจำนวนครั้งที่อ่านเฟรมไม่สำเร็จติดต่อกัน ถ้าเกินเกณฑ์นี้จะปิดกล้อง
  # แล้วเปิดใหม่อัตโนมัติ (แก้ปัญหากล้อง/ไดรเวอร์ค้างระหว่างใช้งาน โดยเฉพาะ
  # backend MSMF บน Windows ที่บางครั้งหลุดกลางคันแล้วอ่านเฟรมไม่ได้อีกเลย)
  consecutive_failures = 0
  MAX_CONSECUTIVE_FAILURES = 30

  while True:
    t0 = time.time()
    try:
      ret, frame = cap.read()
      if not ret:
        consecutive_failures += 1
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
          print(
              f"[CAM] อ่านเฟรมไม่สำเร็จ {consecutive_failures} ครั้งติดต่อกัน "
              f"-> ปิดกล้องแล้วลองเปิดใหม่"
          )
          try:
            cap.release()
          except Exception:
            pass
          with cam_state.lock:
            cam_state.last_payload = cam_state._make_camera_payload(
                opened=False, reason="camera stalled, reconnecting"
            )
          time.sleep(1.0)
          new_cap = open_camera_multi_try()
          if new_cap is not None:
            cap = new_cap
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)
            with cam_state.lock:
              cam_state.last_payload = cam_state._make_camera_payload(
                  opened=True, reason="camera reconnected"
              )
            print("[CAM] เปิดกล้องใหม่สำเร็จ")
          else:
            print("[CAM] เปิดกล้องใหม่ไม่สำเร็จ จะลองอีกครั้งใน 1 วิ")
          consecutive_failures = 0
        time.sleep(0.05)
        continue

      consecutive_failures = 0

      with latest_frame_lock:
        latest_frame = frame.copy()

      active_slots = ultrasonic_state.snapshot()
      zones_pred = classify_frame_into_zones(classifier, frame, active_slots)
      img_b64 = frame_to_jpeg_base64(_draw_zone_overlay(frame, active_slots))
    except Exception as e:
      with cam_state.lock:
        cam_state.last_payload = cam_state._make_camera_payload(
            opened=True, reason=f"camera connected; worker exception: {e}"
        )
      time.sleep(0.5)
      continue

    dt = time.time() - t0
    fps = 1.0 / dt if dt > 0 else 0
    now_ts = time.time()

    for zid, zp in zones_pred.items():
      session_tracker.update(zid, zp.status, now_ts)

    def _zone_decision(z_status: str) -> str:
      if z_status == "Occupied":
        return "CAR"
      if z_status == "NotCar":
        return "NOT_CAR"
      if z_status == "NoClassifier":
        return "NO_CLASSIFIER"
      return "UNKNOWN"

    payload = {
        "img": img_b64,
        "preds": {
            "fps": fps,
            "ts": time.time(),
            "camera": {
                "opened": True,
                "reason": (
                    "ok"
                    if not classifier_reason
                    else f"camera ok; AI classifier failed: {classifier_reason}"
                ),
            },
            "ultrasonic": active_slots,
            "zones": {
                zid: {
                    "status": zp.status,
                    "confidence": float(zp.confidence),
                    "decision": _zone_decision(zp.status),
                    "occupied_since": session_tracker.get_active_start(zid),
                }
                for zid, zp in zones_pred.items()
            },
        },
    }

    with cam_state.lock:
      cam_state.last_payload = payload


threading.Thread(target=camera_worker, daemon=True).start()


def _cors(resp):
  resp.headers["Access-Control-Allow-Origin"] = "*"
  resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
  resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
  return resp


@app.route("/video", methods=["OPTIONS"])
def video_options():
    return _cors(make_response("", 200))


@app.route("/ultrasonic", methods=["OPTIONS"])
def ultrasonic_options():
    return _cors(make_response("", 200))


@app.post("/ultrasonic")
def ultrasonic_endpoint():
    data = request.get_json(silent=True) or {}
    ultrasonic_state.update(data.get("slots", {}))
    resp = make_response(jsonify({"ok": True, "slots": ultrasonic_state.snapshot()}), 200)
    resp.headers["Cache-Control"] = "no-store"
    return _cors(resp)


@app.get("/video")
def video_endpoint():
  with cam_state.lock:
    resp = make_response(jsonify(cam_state.last_payload), 200)
  resp.headers["Cache-Control"] = "no-store"
  return _cors(resp)


@app.get("/history")
def history_endpoint():
  """คืนประวัติการจอดทั้งหมด (หรือกรองเฉพาะช่องเดียวด้วย ?zone=P1)
  แต่ละรายการ: {"zone": "P1", "start_ts": ..., "end_ts": ..., "duration_sec": ...}
  ใช้ทำกราฟ peak/off-peak ฝั่ง frontend"""
  zone = request.args.get("zone", "").strip().upper()
  records = session_tracker.read_history()
  if zone and zone != "ALL":
    records = [r for r in records if r.get("zone") == zone]
  resp = make_response(jsonify({"ok": True, "records": records}), 200)
  resp.headers["Cache-Control"] = "no-store"
  return _cors(resp)


# =========================================================
# เสิร์ฟไฟล์หน้าเว็บเอง (index.html, script.js, cam_ui_inject.js, style.css)
# วางไฟล์เหล่านี้ไว้โฟลเดอร์เดียวกับ cam_ai_server.py แล้วเปิด
# http://127.0.0.1:5000 ได้เลย ไม่ต้องเปิด Live Server
# =========================================================

@app.get("/")
def serve_index():
  return send_from_directory(WEB_ROOT, "index.html")


@app.get("/<path:filename>")
def serve_static_file(filename):
  return send_from_directory(WEB_ROOT, filename)


if __name__ == "__main__":
  index_path = os.path.join(WEB_ROOT, "index.html")
  print(f"[WEB] WEB_ROOT = {WEB_ROOT}")
  print(f"[WEB] เจอไฟล์ index.html ไหม: {os.path.exists(index_path)}")
  app.run(host="0.0.0.0", port=5000, debug=False)