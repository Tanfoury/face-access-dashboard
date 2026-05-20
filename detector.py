# detector.py
import cv2
import os

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "face_detection_yunet_2023mar.onnx")

USE_YUNET = os.path.exists(MODEL_PATH)

if USE_YUNET:
    detector = cv2.FaceDetectorYN.create(
        MODEL_PATH, "",
        (320, 240),          # ? smaller input size
        score_threshold  = 0.6,
        nms_threshold    = 0.3,
        top_k            = 50
    )
    print("[DETECTOR] YuNet loaded")
else:
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    print("[DETECTOR]  Using Haar Cascade")


def detect_faces(frame):
    h, w = frame.shape[:2]

    if USE_YUNET:
        # detect on half-size frame 4x faster
        small  = cv2.resize(frame, (320, 240))
        detector.setInputSize((320, 240))
        _, faces = detector.detect(small)

        boxes = []
        if faces is not None:
            scale_x = w / 320
            scale_y = h / 240 
            for face in faces:
                # scale coordinates back to original size
                x1 = max(0, int(face[0] * scale_x))
                y1 = max(0, int(face[1] * scale_y))
                x2 = min(w, int((face[0] + face[2]) * scale_x))
                y2 = min(h, int((face[1] + face[3]) * scale_y))
                boxes.append((x1, y1, x2, y2))
        return boxes

    else:
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray, 1.1, 5, minSize=(60, 60)
        )
        return [(x, y, x+w, y+h) for (x, y, w, h) in faces]
