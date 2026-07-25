import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2
import numpy as np
import tensorflow as tf

# โหลดโมเดล
model = tf.keras.models.load_model("Model/keras_model.h5")

# โหลดชื่อคลาส
with open("Model/labels.txt", "r", encoding="utf-8") as f:
    class_names = [line.strip() for line in f.readlines()]

# เปิดกล้อง
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# ตั้งค่าความละเอียดกล้อง
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    # เตรียมภาพสำหรับโมเดล Teachable Machine
    image = cv2.resize(frame, (224, 224))
    image = np.asarray(image, dtype=np.float32)
    image = (image / 127.5) - 1
    image = np.expand_dims(image, axis=0)

    # ทำนายผล
    prediction = model.predict(image, verbose=0)

    index = np.argmax(prediction)
    class_name = class_names[index]
    confidence_score = prediction[0][index]

    # แสดงผลบนจอ
    text = f"{class_name} ({confidence_score*100:.1f}%)"

    cv2.putText(
        frame,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("Teachable Machine", frame)

    # กด Q เพื่อออก
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

