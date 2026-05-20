# main3.py
import os
import cv2
import time
import threading
import socket
from datetime import datetime
import queue

_lcd_queue = queue.Queue()
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
# Import your optimized C++ blob device detector
from device_detector import init_yolo, detect_spoof_devices

# Explicitly ensure Faiss does not launch resource-hogging internal thread pools
try:
    import faiss
    faiss.omp_set_num_threads(1)
    print("[FAISS] Locked search execution to 1 thread for maximum CPU efficiency.")
except ImportError:
    pass

# -- Cooldowns & Controls -----------------------------------------------------
ENTRY_EXIT_COOLDOWN = 30
ALARM_COOLDOWN = 4.0      # Protects the CPU loop from getting clogged by hardware delays
_last_alarm_time = 0

# -- Global Threat Trackers ---------------------------------------------------
_spoof_detected = False
_tracked_spoof_boxes = [] 
_threat_lock = threading.Lock()

# -- LCD Setup ---------------------------------------------------------------
LCD_ENABLED = True
LCD_ADDRESS = 0x27        

lcd            = None
_lcd_lock      = threading.Lock()
_lcd_current   = ("", "")  
_lcd_last_msg_time = {}    

def lcd_show_for_label(label, line1, line2="", auto_clear_sec=0, cooldown=5):
    now = time.time()
    if now - _lcd_last_msg_time.get(label, 0) > cooldown:
        lcd_show(line1, line2, auto_clear_sec)
        _lcd_last_msg_time[label] = now

def lcd_init():
    global lcd, LCD_ENABLED, _lcd_queue
    import queue
    _lcd_queue = queue.Queue()
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(
            'PCF8574', LCD_ADDRESS, port=1, cols=16, rows=2,
            dotsize=8, charmap='A02', auto_linebreaks=False
        )
        lcd.clear()
        time.sleep(0.05)
        print("[LCD] LCD initialized successfully")
        threading.Thread(target=_lcd_writer_thread, daemon=True).start()
        lcd_show("Access System", "Starting...")
    except Exception as e:
        print(f"[LCD] Failed to initialize: {e}")
        LCD_ENABLED = False

def _lcd_writer_thread():
    global _lcd_current
    while True:
        try:
            line1, line2 = _lcd_queue.get(timeout=1)
            if (line1, line2) == _lcd_current:
                _lcd_queue.task_done()
                continue
            with _lcd_lock:
                lcd.cursor_pos = (0, 0)
                lcd.write_string(line1.ljust(16)[:16])
                time.sleep(0.01)
                lcd.cursor_pos = (1, 0)
                lcd.write_string(line2.ljust(16)[:16])
            _lcd_current = (line1, line2)
            _lcd_queue.task_done()
        except Exception:
            pass   

def lcd_show(line1, line2="", auto_clear_sec=0):
    if not LCD_ENABLED or _lcd_queue is None:
        return
    _lcd_queue.put((line1[:16], line2[:16]))
    if auto_clear_sec > 0:
        def _reset():
            time.sleep(auto_clear_sec)
            with _labels_lock:
                if not _face_labels:
                    _lcd_queue.put(("Access System", "Ready..."))
        threading.Thread(target=_reset, daemon=True).start()


# -- GPIO --------------------------------------------------------------------
if GPIO_ENABLED:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    for pin in [LED_GREEN, LED_RED, LED_YELLOW, BUZZER_PIN]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    print("[GPIO] GPIO ready")
else:
    print("[GPIO] PC mode -- GPIO disabled")

# -- Shared state ------------------------------------------------------------
_latest_frame  = None
_frame_lock    = threading.Lock()

_face_labels   = {}
_labels_lock   = threading.Lock()

_recog_active  = set()
_recog_lock    = threading.Lock()

_last_action   = {}
_running       = True
_frame_count   = 0

LABEL_TIMEOUT  = 1.5 # Adjusted to eliminate flickering when the Pi runs heavy processing tasks


# -- GPIO helpers ------------------------------------------------------------

def green_flash():
    if not GPIO_ENABLED:
        print("[DOOR] Unlock (GPIO Disabled)")
        return
    try:
        import RPi.GPIO as GPIO
        GPIO.output(LED_GREEN, GPIO.HIGH)
        time.sleep(UNLOCK_SECONDS)
        GPIO.output(LED_GREEN, GPIO.LOW)
    except Exception as e:
        print(f"[DOOR] Error controlling LED: {e}")

def red_alert():
    if not GPIO_ENABLED:
        print("[DOOR] Reject")
        return
    GPIO.output(LED_RED, GPIO.HIGH)
    buzzer = GPIO.PWM(BUZZER_PIN, 1000)
    buzzer.start(50)
    time.sleep(0.3)
    buzzer.stop()
    time.sleep(1.2)
    GPIO.output(LED_RED, GPIO.LOW)

def wifi_monitor_thread():
    while _running:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            if GPIO_ENABLED:
                GPIO.output(LED_YELLOW, GPIO.LOW)
        except OSError:
            if GPIO_ENABLED:
                GPIO.output(LED_YELLOW, GPIO.HIGH)
        time.sleep(5)  


# -- Access logic ------------------------------------------------------------

def handle_access(name):
    now     = time.time()
    student = get_student_by_name(name)

    if student is None:
        lcd_show_for_label(name, "NOT REGISTERED", name[:16], auto_clear_sec=3, cooldown=10)
        return f"{name} - Not registered", (0, 165, 255), False

    if name in _last_action:
        elapsed = now - _last_action[name]["time"]
        if elapsed < ENTRY_EXIT_COOLDOWN:
            remaining = int(ENTRY_EXIT_COOLDOWN - elapsed)
            lcd_show_for_label(name, f"Wait {remaining}s", name[:16], auto_clear_sec=2, cooldown=5)
            return f"{name} - Wait {remaining}s", (0, 165, 255), False

    if not has_entry_today(name):
        action = "ENTRY"
    elif is_inside(name):
        if has_exit_today(name):
            lcd_show_for_label(name, "Done Today", name[:16], auto_clear_sec=3, cooldown=10)
            return f"{name} - Done today", (128, 128, 128), False
        action = "EXIT"
    else:
        lcd_show_for_label(name, "Done Today", name[:16], auto_clear_sec=3, cooldown=10)
        return f"{name} - Done today", (128, 128, 128), False

    log_access(student.student_id, name, True, action)
    update_inside(name, action == "ENTRY")
    _last_action[name] = {"action": action, "time": now}

    threading.Thread(target=green_flash, daemon=True).start()

    if action == "ENTRY":
        lcd_show_for_label(name, "Welcome!", name[:16], auto_clear_sec=4, cooldown=0)
    else:
        lcd_show_for_label(name, "Goodbye!", name[:16], auto_clear_sec=4, cooldown=0)

    color = (0, 255, 0) if action == "ENTRY" else (0, 255, 100)
    print(f"[ACCESS] {action} -- {name} at {datetime.now().strftime('%H:%M:%S')}")
    return f"{name} - {action}", color, True


# -- Thread 1: Camera capture ------------------------------------------------

def camera_capture_thread(camera):
    global _latest_frame, _running
    while _running:
        ret, frame = camera.read()
        if ret and frame is not None:
            with _frame_lock:
                _latest_frame = frame


# -- Thread 2: Detection Loop -------------------------------------------------

def detection_thread():
    global _running, _frame_count, _spoof_detected, _tracked_spoof_boxes, _last_alarm_time

    # Change tracking from frame counts to an absolute epoch timestamp
    _first_face_seen_time = None
    
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
        boxes = detect_faces(frame)
        now   = time.time()

        # Run optimized device checker
        if len(boxes) > 0 and _frame_count % 3 == 0:
            is_spoof, found_boxes = detect_spoof_devices(frame)
            with _threat_lock:
                _spoof_detected = is_spoof
                _tracked_spoof_boxes = found_boxes
        elif len(boxes) == 0:
            with _threat_lock:
                _spoof_detected = False
                _tracked_spoof_boxes = []

        # Rate-limit physical alert outputs
        if _spoof_detected and (now - _last_alarm_time > ALARM_COOLDOWN):
            _last_alarm_time = now
            lcd_show_for_label("GlobalSpoof", "SPOOF ATTEMPT", "ACCESS DENIED", auto_clear_sec=2, cooldown=3)
            threading.Thread(target=red_alert, daemon=True).start()

        if len(boxes) == 0:
            _first_face_seen_time = None  # Reset clock when room is empty

        current_keys = set()
        for (x1, y1, x2, y2) in boxes:
            cx       = ((x1 + x2) // 2) // 200 * 200
            cy       = ((y1 + y2) // 2) // 200 * 200
            face_key = (cx, cy)
            current_keys.add(face_key)

            if _first_face_seen_time is None:
                _first_face_seen_time = now  # Start the security timer the exact millisecond a face hits the sensor

            elapsed_security_wait = now - _first_face_seen_time

            with _labels_lock:
                if face_key in _face_labels:
                    _face_labels[face_key]["bbox"]      = (x1, y1, x2, y2)
                    _face_labels[face_key]["last_seen"] = now
                else:
                    _face_labels[face_key] = {
                        "label":     "Verifying..." if elapsed_security_wait < 0.15 else "Scanning...",
                        "color":     (0, 165, 255),
                        "bbox":      (x1, y1, x2, y2),
                        "last_seen": now
                    }
                
                if _lcd_queue.qsize() == 0 and not _spoof_detected and face_key not in _recog_active:
                    lcd_show("Verifying...", "Please wait")

            # 🛡️ THE SPEED OPTIMIZATION: Wait exactly 150 milliseconds. 
            # This is completely unnoticeable to humans but gives YOLO plenty of time to claim the frame.
            if _frame_count % FRAME_SKIP == 0 and not _spoof_detected:
                if elapsed_security_wait >= 0.15:  
                    with _recog_lock:
                        if face_key not in _recog_active:
                            _recog_active.add(face_key)
                            threading.Thread(
                                target=recognize_worker,
                                args=(frame, (x1, y1, x2, y2), face_key),
                                daemon=True
                            ).start()

        with _labels_lock:
            stale = [k for k, v in _face_labels.items()
                     if now - v["last_seen"] > LABEL_TIMEOUT]
            for k in stale:
                _face_labels.pop(k, None)

        time.sleep(0.01)

# -- Thread 3: Recognition worker --------------------------------------------

def recognize_worker(frame, bbox, face_key):
    global _spoof_detected, _last_alarm_time
    label = "Scanning..."
    color = (0, 165, 255)
    try:
        if _spoof_detected:
            label = "SPOOF DETECTED ❌"
            color = (0, 0, 255)
            return

        cached_name = None
        with _labels_lock:
            if face_key in _face_labels and "name" in _face_labels[face_key]:
                cached_name = _face_labels[face_key]["name"]
                cached_sim = _face_labels[face_key]["sim"]
        
        if cached_name is not None:
            name, sim = cached_name, cached_sim
        else:
            name, sim = recognize_face(frame, bbox) # Leverages Faiss in face_db
            with _labels_lock:
                if face_key in _face_labels:
                    _face_labels[face_key]["name"] = name
                    _face_labels[face_key]["sim"] = sim

        if _spoof_detected:
            label = "SPOOF DETECTED ❌"
            color = (0, 0, 255)
            return

        if name != "Unknown":
            label, color, granted = handle_access(name)
            if not granted and "Wait" not in label and "Done" not in label:
                now = time.time()
                if now - _last_alarm_time > ALARM_COOLDOWN:
                    _last_alarm_time = now
                    threading.Thread(target=red_alert, daemon=True).start()
        else:
            label = f"Unknown ({sim:.0%})"
            color = (0, 0, 255)
            lcd_show_for_label("Unknown", "ACCESS DENIED", "Unknown Person", auto_clear_sec=3, cooldown=5)
            now = time.time()
            if now - _last_alarm_time > ALARM_COOLDOWN:
                _last_alarm_time = now
                threading.Thread(target=red_alert, daemon=True).start()

    except Exception as e:
        print(f"[RECOG] worker error: {e}")
        label = "Error"
        color = (0, 0, 255)
    finally:
        with _labels_lock:
            if face_key in _face_labels:
                if _spoof_detected:
                    _face_labels[face_key]["label"] = "SPOOF DETECTED ❌"
                    _face_labels[face_key]["color"] = (0, 0, 255)
                else:
                    _face_labels[face_key]["label"] = label
                    _face_labels[face_key]["color"] = color
        with _recog_lock:
            _recog_active.discard(face_key)


# -- Main thread: Display ----------------------------------------------------

def run():
    global _running, _spoof_detected, _tracked_spoof_boxes

    init_db()
    daily_reset()
    lcd_init()

    print("[SYSTEM] Initializing models...")
    initialize()  
    init_yolo()    

    wifi_thread = threading.Thread(target=wifi_monitor_thread, daemon=True)
    wifi_thread.start()

    camera = Camera()

    t1 = threading.Thread(target=camera_capture_thread, args=(camera,), daemon=True)
    t2 = threading.Thread(target=detection_thread, daemon=True)
    t1.start()
    t2.start()

    print("[SYSTEM] Waiting for camera...")
    while _latest_frame is None:
        time.sleep(0.05)

    print("[SYSTEM] Access system running with Anti-Spoof Protection active.\n")
    lcd_show("Access System", "Ready...")

    fps_time = time.time()

    while True:
        with _frame_lock:
            if _latest_frame is None:
                continue
            display = _latest_frame.copy()

        # 1. Render Face Trackers
        with _labels_lock:
            labels_copy = dict(_face_labels)

        for face_key, info in labels_copy.items():
            x1, y1, x2, y2 = info["bbox"]
            display_color = (0, 0, 255) if _spoof_detected else info["color"]
            display_label = "SPOOF DETECTED ❌" if _spoof_detected else info["label"]

            cv2.rectangle(display, (x1, y1), (x2, y2), display_color, 2)
            cv2.putText(
                display, display_label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, display_color, 2
            )

        # 2. Render Explicit Electronics Threat Coordinates
        with _threat_lock:
            local_spoof_boxes = list(_tracked_spoof_boxes)

        for (sx1, sy1, sx2, sy2, cid) in local_spoof_boxes:
            label_text = "PHONE THREAT" if cid == 67 else "SCREEN THREAT"
            cv2.rectangle(display, (sx1, sy1), (sx2, sy2), (0, 0, 255), 3)
            cv2.putText(
                display, f"⚠️ {label_text}", (sx1, sy1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2
            )

        now      = time.time()
        fps      = 1.0 / max(now - fps_time, 1e-6)
        fps_time = now
        cv2.putText(
            display, f"FPS: {fps:.0f}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
        )

        cv2.imshow("Access System", display)

        if cv2.waitKey(5) & 0xFF == ord("q"):
            _running = False
            break

    camera.release()
    cv2.destroyAllWindows()
    if GPIO_ENABLED:
        GPIO.cleanup()
    if LCD_ENABLED and lcd is not None:
        lcd_show("System Stopped", "Goodbye!")
        time.sleep(2)
        with _lcd_lock:
            lcd.clear()
    print("[SYSTEM] System stopped.")


if __name__ == "__main__":
    run()