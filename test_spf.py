# test_spf.py
import cv2
import time
import os
import sys

os.chdir('/home/pi/Desktop/rasp')
sys.path.insert(0, '/home/pi/Desktop/rasp')

from camera import Camera
from device_detector import init_yolo, detect_targets

# Boot up the single unified tracker
init_yolo()
cam = Camera()

print("\n🚀 Single-Model Anti-Spoof System Engaged.")
print("Monitoring frame for user presence and phone/laptop threats...")
print("Press Q to quit.\n")

while True:
    ret, frame = cam.read()
    if not ret or frame is None:
        continue

    # Execute a single pipeline pass per frame
    all_detections = detect_targets(frame)
    
    # Split detections based on what they are
    people = [d for d in all_detections if d[4] == 0]              # Class 0
    spoofs = [d for d in all_detections if d[4] in [63, 67]]       # Classes 63, 67

    spoof_detected = len(spoofs) > 0

    # 1. Handle User/Person boxes
    for (x1, y1, x2, y2, cid, conf) in people:
        if spoof_detected:
            color, label = (0, 0, 255), "SPOOF ATTACK DETECTED ❌"
        else:
            color, label = (0, 255, 0), "USER ACCESS REAL ✅"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{label} ({conf:.2f})", (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # 2. Handle Rogue Electronic Devices boxes
    for (dx1, dy1, dx2, dy2, cid, conf) in spoofs:
        dev_name = "Mobile Phone" if cid == 67 else "Computer Screen"
        
        # Draw explicit warning boxes around the electronic threat
        cv2.rectangle(frame, (dx1, dy1), (dx2, dy2), (0, 0, 255), 2)
        cv2.putText(frame, f"MALICIOUS DETECTOR: {dev_name}", (dx1, dy1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 2)

    # Output window
    cv2.imshow("Unified YOLO Tracking Node", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()