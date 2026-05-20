import os
import cv2
import time
import threading
from datetime import datetime
 
from camera import Camera
from detector import detect_faces
from config import (
    BASE_DIR, FRAME_SKIP,
    GPIO_ENABLED, LED_GREEN, LED_RED, LED_YELLOW,
    BUZZER_PIN, UNLOCK_SECONDS
)
from face_db import initialize, recognize_face
from database1 import (
    init_db, daily_reset,
    get_student_by_name, log_access,
    is_inside, update_inside,
    has_entry_today, has_exit_today
)
 
# -- Cooldown ----------------------------------------------------------------
ENTRY_EXIT_COOLDOWN = 30
 
# -- GPIO --------------------------------------------------------------------
if GPIO_ENABLED:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    for pin in [LED_GREEN, LED_RED, LED_YELLOW, BUZZER_PIN]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    print("[GPIO] GPIO ready")
else:
    print("[GPIO] PC mode  GPIO disabled")
 
# -- Shared state ------------------------------------------------------------
_latest_frame  = None
_frame_lock    = threading.Lock()
 
_face_labels   = {}       # { face_key: {label, color, bbox, last_seen} }
_labels_lock   = threading.Lock()
 
_recog_active  = set()
_recog_lock    = threading.Lock()
 
_last_action   = {}
_running       = True
_frame_count   = 0
 
# how long to keep a label after face disappears (seconds)
LABEL_TIMEOUT  = 0.5
 
 
# -- GPIO helpers ------------------------------------------------------------
 
def green_flash():
    if not GPIO_ENABLED:
        print("[DOOR]  Unlock")
        return
    GPIO.output(LED_GREEN, GPIO.HIGH)
    
    time.sleep(UNLOCK_SECONDS)
    
    GPIO.output(LED_GREEN, GPIO.LOW)
 
def red_alert():
    if not GPIO_ENABLED:
        print("[DOOR] Reject")
        return

    GPIO.output(LED_RED, GPIO.HIGH)

    # PWM for passive buzzer
    buzzer = GPIO.PWM(BUZZER_PIN, 1000)  # 1000 Hz tone
    buzzer.start(50)                      # 50% duty cycle
    time.sleep(0.3)
    buzzer.stop()

    time.sleep(1.7)
    GPIO.output(LED_RED, GPIO.LOW)
 
 
# -- Access logic --------------
def handle_access(name):
    now     = time.time()
    student = get_student_by_name(name)
 
    if student is None:
        return f"{name} - Not registered", (0, 165, 255), False
 
    if name in _last_action:
        elapsed = now - _last_action[name]["time"]
        if elapsed < ENTRY_EXIT_COOLDOWN:
            remaining = int(ENTRY_EXIT_COOLDOWN - elapsed)
            return f"{name} - Wait {remaining}s", (0, 165, 255), False
 
    if not has_entry_today(name):
        action = "ENTRY"
    elif is_inside(name):
        if has_exit_today(name):
            return f"{name} - Done today", (128, 128, 128), False
        action = "EXIT"
    else:
        return f"{name} - Done today", (128, 128, 128), False
 
    log_access(student.student_id, name, True, action)
    update_inside(name, action == "ENTRY")
    _last_action[name] = {"action": action, "time": now}
 
    threading.Thread(target=green_flash, daemon=True).start()
 
    color = (0, 255, 0) if action == "ENTRY" else (0, 255, 100)
    print(f"[ACCESS] ? {action} ? {name} at {datetime.now().strftime('%H:%M:%S')}")
    return f"{name} - {action} ?", color, True
 
 
# -- Thread 1: Camera capture ------------------------------------------------
 
def camera_capture_thread(camera):
    global _latest_frame, _running
    while _running:
        ret, frame = camera.read()
        if ret and frame is not None:
            with _frame_lock:
                _latest_frame = frame
 
 
# -- Thread 2: Detection -----------------------------------------------------
 
def detection_thread():
    global _running, _frame_count
 
    while _running:
        with _frame_lock:
            if _latest_frame is None:
                time.sleep(0.033)
                continue
            frame = _latest_frame.copy()
            frame_hash = hash(frame[::10, ::10].tobytes())

            if hasattr(detection_thread, 'last_hash') and detection_thread.last_hash == frame_hash:
                time.sleep(0.033)
                continue
            detection_thread.last_hash = frame_hash
 
        _frame_count += 1
 
        # detect faces
        boxes = detect_faces(frame)
 
        now = time.time()
 
        # build current face keys from detected boxes
        current_keys = set()
        for (x1, y1, x2, y2) in boxes:
            cx       = ((x1 + x2) // 2) // 300 * 300
            cy       = ((y1 + y2) // 2) // 300 * 300
            face_key = (cx, cy)
            current_keys.add(face_key)
 
            # update or create label
            with _labels_lock:
                if face_key in _face_labels:
                    _face_labels[face_key]["bbox"]      = (x1, y1, x2, y2)
                    _face_labels[face_key]["last_seen"] = now
                else:
                    _face_labels[face_key] = {
                        "label":     "Scanning...",
                        "color":     (0, 165, 255),
                        "bbox":      (x1, y1, x2, y2),
                        "last_seen": now
                    }
 
            # trigger recognition
            if _frame_count % FRAME_SKIP == 0:
                with _recog_lock:
                    if face_key not in _recog_active:
                        _recog_active.add(face_key)
                        threading.Thread(
                            target = recognize_worker,
                            args   = (frame, (x1, y1, x2, y2), face_key),
                            daemon = True
                        ).start()
 
        # -- CLEANUP remove stale labels --
        with _labels_lock:
            stale = [
                k for k, v in _face_labels.items()
                if now - v["last_seen"] > LABEL_TIMEOUT
            ]
            for k in stale:
                _face_labels.pop(k, None)
 
        time.sleep(0.01)
# -- Thread 3: Recognition worker --------------------------------------------
 
def recognize_worker(frame, bbox, face_key):
    try:
        name, sim = recognize_face(frame, bbox)
 
        if name != "Unknown":
            label, color, granted = handle_access(name)
            if not granted and "Wait" not in label and "Done" not in label:
                threading.Thread(target=red_alert, daemon=True).start()
        else:
            label = f"Unknown ({sim:.0%})"
            color = (0, 0, 255)
            threading.Thread(target=red_alert, daemon=True).start()
 
    except Exception as e:
        print(f"[RECOG] Error: {e}")
        label = "Error"
        color = (0, 165, 255)
 
    finally:
        with _labels_lock:
            if face_key in _face_labels:
                _face_labels[face_key]["label"] = label
                _face_labels[face_key]["color"] = color
        with _recog_lock:
            _recog_active.discard(face_key)
 
 
# -- Main thread: Display ----------------------------------------------------
 
def run():
    global _running
 
    init_db()
    daily_reset()
 
    print("[SYSTEM] Initializing face recognition...")
    initialize()
 
    camera = Camera()
 
    t1 = threading.Thread(target=camera_capture_thread, args=(camera,), daemon=True)
    t2 = threading.Thread(target=detection_thread, daemon=True)
    t1.start()
    t2.start()
 
    print("[SYSTEM] Waiting for camera...")
    while _latest_frame is None:
        time.sleep(0.05)
 
    print("[SYSTEM] ? Access system running. Press Q to stop.\n")
 
    fps_time = time.time()
 
    while True:
        with _frame_lock:
            
            if _latest_frame is None:
                continue
            display = _latest_frame.copy()
 
        with _labels_lock:
            labels_copy = dict(_face_labels)
 
        for face_key, info in labels_copy.items():
            x1, y1, x2, y2 = info["bbox"]
            cv2.rectangle(display, (x1, y1), (x2, y2), info["color"], 2)
            cv2.putText(
                display, info["label"],
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, info["color"], 2
            )
 
        now      = time.time()
        fps      = 1.0 / max(now - fps_time, 1e-6)
        fps_time = now
        cv2.putText(
            display, f"FPS: {fps:.0f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (255, 255, 0), 2
        )
 
        supervision_path = os.path.join(BASE_DIR, "supervision.jpg")
        cv2.imwrite(supervision_path, display)
        cv2.imshow("Access System", display)
 
        if cv2.waitKey(5) & 0xFF == ord("q"):
            _running = False
            break
 
    camera.release()
    cv2.destroyAllWindows()
    if GPIO_ENABLED:
        GPIO.cleanup()
    print("[SYSTEM] System stopped.")
 
 
if __name__ == "__main__":
    run()
 
