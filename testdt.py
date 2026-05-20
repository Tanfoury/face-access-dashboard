import cv2
import time
from detector import detect_faces
from camera import Camera

cam = Camera()

print("Warming up camera...")
frame = None
for i in range(10):
    ret, frame = cam.read()
    if ret and frame is not None:
        break
    time.sleep(0.1)

if frame is None:
    print("Camera failed!")
else:
    print(f"Frame shape: {frame.shape}")

    start = time.time()
    for i in range(10):
        boxes = detect_faces(frame)
    elapsed = time.time() - start

    print(f"Haar cascade x10: {elapsed:.2f}s")
    print(f"Per frame:        {elapsed/10:.3f}s")
    print(f"Boxes found:      {len(boxes)}")

cam.release()
