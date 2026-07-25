import cv2
import time


def try_open_indices(max_index: int = 5) -> bool:
    # Console-only camera debug (no cv2.imshow), because GUI may not appear.
    backend_candidates = [
        ("DSHOW", getattr(cv2, "CAP_DSHOW", None)),
        ("MSMF", getattr(cv2, "CAP_MSMF", None)),
    ]

    for i in range(max_index):
        for backend_name, backend in backend_candidates:
            if backend is None:
                continue

            cap = cv2.VideoCapture(i, backend)
            opened = cap.isOpened()
            print(f"[index {i}] backend={backend_name} isOpened={opened}")

            if opened:
                # warmup / try multiple reads
                for attempt in range(3):
                    ret, frame = cap.read()
                    if ret:
                        print(
                            f"[index {i}] backend={backend_name} read attempt={attempt} ret={ret} frame_shape={frame.shape}"
                        )
                        cap.release()
                        return True

                    print(
                        f"[index {i}] backend={backend_name} read attempt={attempt} ret={ret}"
                    )
                    time.sleep(0.05)

            cap.release()

    return False


if __name__ == "__main__":
    ok = try_open_indices(5)
    print("CAM_OPEN_OK" if ok else "CAM_OPEN_FAILED")

