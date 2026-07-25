'''import cv2
import numpy as np
from tensorflow import keras
import os


class TeachableMachineImageModel:
    def __init__(self, model_path, labels_path):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"ไม่พบโมเดล: {model_path}")

        if not os.path.exists(labels_path):
            raise FileNotFoundError(f"ไม่พบ labels: {labels_path}")

        self.model = keras.models.load_model(model_path)
        self.class_names = self.load_labels(labels_path)

        self.cap = None

    def load_labels(self, labels_path):
        class_names = []

        with open(labels_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if line == "":
                    continue

                parts = line.split(" ", 1)

                if len(parts) == 2:
                    class_names.append(parts[1])
                else:
                    class_names.append(parts[0])

        return class_names

    def setup_webcam(self, width=640, height=480):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise Exception("ไม่สามารถเปิดกล้องเว็บแคมได้")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def preprocess_frame(self, frame):
        img = cv2.resize(frame, (224, 224))
        img = img.astype(np.float32)

        # สำหรับโมเดล Teachable Machine
        img = (img / 127.5) - 1

        img = np.expand_dims(img, axis=0)

        return img

    def predict(self, frame):
        img = self.preprocess_frame(frame)

        predictions = self.model.predict(
            img,
            verbose=0
        )[0]

        best_index = np.argmax(predictions)
        confidence = predictions[best_index]

        class_name = self.class_names[best_index]

        return class_name, confidence, predictions

    def start(self):
        if self.cap is None:
            self.setup_webcam()

        while True:
            ret, frame = self.cap.read()

            if not ret:
                print("อ่านภาพจากกล้องไม่สำเร็จ")
                break

            class_name, confidence, predictions = self.predict(frame)

            text = f"{class_name}: {confidence * 100:.2f}%"

            cv2.putText(
                frame,
                text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            y = 80

            for i, prob in enumerate(predictions):
                label = f"{self.class_names[i]}: {prob * 100:.2f}%"

                cv2.putText(
                    frame,
                    label,
                    (20, y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    2
                )

                y += 30

            cv2.imshow(
                "Teachable Machine Webcam",
                frame
            )

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        self.cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    # อ้างอิง path ตามที่ไฟล์นี้อยู่จริง (กันรันจากโฟลเดอร์อื่นแล้วไฟล์ไม่เจอ)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    MODEL_PATH = os.path.join(BASE_DIR, "Model", "keras_model.h5")
    LABELS_PATH = os.path.join(BASE_DIR, "Model", "labels.txt")

    model = TeachableMachineImageModel(
        MODEL_PATH,
        LABELS_PATH
    )

    model.setup_webcam(640, 480)
    model.start()

'''
from tensorflow import keras

print("Keras ใช้งานได้")
print(keras.__version__)