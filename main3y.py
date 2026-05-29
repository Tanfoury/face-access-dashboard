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
    has_entry_today, has_exit_today,
    clear_all_logs
)

# -- Cooldown ------------555----5------55---------------------777---------------------
ENTRY_EXIT_COOLDOWN = 30

# -- LCD Setup ---------------------------------------------------------------
LCD_ENABLED = True
LCD_ADDRESS = 0x27        # Change to 0x3F if needed

lcd            = None
_lcd_lock      = threading.Lock()
_lcd_queue     = None     # will be set after import
_lcd_current   = ("", "")  # track what's currently shown to avoid flicker
_lcd_last_msg_time = {}    # track when we last showed a message for a specific label

def lcd_show_for_label(label, line1, line2="", auto_clear_sec=0, cooldown=5):
    now = time.time()
    if now - _lcd_last_msg_time.get(label, 0) > cooldown:
        lcd_show(line1, line2, auto_clear_sec)
        _lcd_last_msg_time[label] = now


def lcd_init():
    """Initialize LCD in its own thread to avoid blocking."""
    global lcd, LCD_ENABLED, _lcd_queue
    import queue
    _lcd_queue = queue.Queue()
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(
            'PCF8574',
            LCD_ADDRESS,
            port=1,
            cols=16,
            rows=2,
            dotsize=8,
            charmap='A02',      # <-- fixes weird symbols
            auto_linebreaks=False
        )
        lcd.clear()
        time.sleep(0.05)
        print("[LCD] LCD initialized successfully")
        # Start the dedicated LCD writer thread
        threading.Thread(target=_lcd_writer_thread, daemon=True).start()
        lcd_show("Access System", "Starting...")
    except Exception as e:
        print(f"[LCD] Failed to initialize: {e}")
        LCD_ENABLED = False


def _lcd_writer_thread():
    """
    Dedicated thread that reads from the queue and writes to LCD.
    This keeps ALL lcd I/O off the main thread -> no lag.
    """
    global _lcd_current
    while True:
        try:
            line1, line2 = _lcd_queue.get(timeout=1)
            # Skip if same message already shown
            if (line1, line2) == _lcd_current:
                _lcd_queue.task_done()
                continue
            with _lcd_lock:
                # Write line 1
                lcd.cursor_pos = (0, 0)
                lcd.write_string(line1.ljust(16)[:16])
                time.sleep(0.01)
                # Write line 2
                lcd.cursor_pos = (1, 0)
                lcd.write_string(line2.ljust(16)[:16])
            _lcd_current = (line1, line2)
            _lcd_queue.task_done()
        except queue.Empty:
            if _lcd_current[0] == "Access System" or _lcd_current[0] == "":
                now = datetime.now()
                date_str = now.strftime("%d/%m/%Y")
                heure_str = now.strftime("    %H:%M:%S")
                try:
                    with _lcd_lock:
                        lcd.cursor_pos = (0, 0)
                        lcd.write_string(date_str.ljust(16)[:16])
                        time.sleep(0.01)
                        lcd.cursor_pos = (1, 0)
                        lcd.write_string(heure_str.ljust(16)[:16])
                except Exception as e:
                    print(f"LCD Write Error: {e}")
        except Exception as e:
            print(f"LCD Thread Error: {e}")


def lcd_show(line1, line2="", auto_clear_sec=0):
    """
    Queue a message to show on LCD (non-blocking, never slows main thread).
    If auto_clear_sec > 0, queues a 'Ready' message after that delay.
    """
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
_global_buzzer = None
if GPIO_ENABLED:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    for pin in [LED_GREEN, LED_RED, LED_YELLOW, BUZZER_PIN]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    _global_buzzer = GPIO.PWM(BUZZER_PIN, 1000)
    _global_buzzer.start(0)  # Start with 0 duty cycle (silent)
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

LABEL_TIMEOUT  = 0.2


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
    if _global_buzzer is not None:
        try:
            _global_buzzer.ChangeDutyCycle(50)
            time.sleep(0.3)
            _global_buzzer.ChangeDutyCycle(0)
        except Exception as e:
            print(f"[BUZZER ERROR] {e}")
    else:
        time.sleep(0.3)
    time.sleep(1.7)
    GPIO.output(LED_RED, GPIO.LOW)

def wifi_monitor_thread():
    """Continuously checks Wi-Fi/Internet and toggles the yellow LED if disconnected."""
    while _running:
        try:
            # Check connection to an external reliable IP (e.g. Google DNS)
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            # We have connection -> Turn off Yellow LED
            if GPIO_ENABLED:
                GPIO.output(LED_YELLOW, GPIO.LOW)
        except OSError:
            # No connection -> Turn on Yellow LED
            if GPIO_ENABLED:
                GPIO.output(LED_YELLOW, GPIO.HIGH)
        time.sleep(5)  # check every 5 seconds

def scheduled_maintenance_thread():
    """ Runs daily reset and clear tasks automatically every 24 hours. """
    while _running:
        now = datetime.now()
        # Schedule at midnight (e.g., 00:00:00)
        # We check roughly every minute
        if now.hour == 0 and now.minute == 0:
            print("[MAINTENANCE] Running automatic daily reset and logs cleanup...")
            try:
                daily_reset() # This now includes cleanup_old_logs(30)
            except Exception as e:
                print(f"[MAINTENANCE] Error: {e}")
            # sleep to avoid re-triggering in the same minute
            time.sleep(60)
        time.sleep(30)


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

    time_str = datetime.now().strftime("%H:%M:%S")
    if action == "ENTRY":
        lcd_show_for_label(name, name[:16], f"In : {time_str}", auto_clear_sec=4, cooldown=0)
    else:
        lcd_show_for_label(name, name[:16], f"Out: {time_str}", auto_clear_sec=4, cooldown=0)

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
        boxes = detect_faces(frame)
        now   = time.time()

        current_keys = set()
        for (x1, y1, x2, y2) in boxes:
            cx       = ((x1 + x2) // 2) // 200 * 200
            cy       = ((y1 + y2) // 2) // 200 * 200
            face_key = (cx, cy)
            current_keys.add(face_key)

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
                if _lcd_queue.qsize() == 0:
                    lcd_show("Scanning...", "Please wait")

            if _frame_count % FRAME_SKIP == 0:
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
    try:
        # OPTIMISATION MASSSIVE : On empêche InsightFace de ralentir la boucle pendant l'attente du Clignement !
        cached_name = None
        with _labels_lock:
            if face_key in _face_labels and "name" in _face_labels[face_key]:
                cached_name = _face_labels[face_key]["name"]
                cached_sim = _face_labels[face_key]["sim"]
        
        if cached_name is not None:
            # On a DÉJÀ vérifié le visage, pas besoin du lourd InsightFace
            name, sim = cached_name, cached_sim
        else:
            # PREMIER PASSAGE : on fait bosser InsightFace (lourd)
            name, sim = recognize_face(frame, bbox)
            
            if name == "Unknown":
                with _labels_lock:
                    if face_key in _face_labels:
                        _face_labels[face_key].setdefault("unknown_count", 0)
                        _face_labels[face_key]["unknown_count"] += 1
                        
                        if _face_labels[face_key]["unknown_count"] >= 3:
                            # Only solidily confirm 'Unknown' after a few tries
                            _face_labels[face_key]["name"] = name
                            _face_labels[face_key]["sim"] = sim
            else:
                with _labels_lock:
                    if face_key in _face_labels:
                        _face_labels[face_key]["name"] = name
                        _face_labels[face_key]["sim"] = sim

        if name != "Unknown":
            # Normal entry logic (no anti-spoof)
            label, color, granted = handle_access(name)
            if not granted and "Wait" not in label and "Done" not in label:
                threading.Thread(target=red_alert, daemon=True).start()
        else:
            # Check if we should buzz yet
            should_buzz = False
            with _labels_lock:
                if face_key in _face_labels and _face_labels[face_key].get("unknown_count", 0) == 3:
                    # Buzz only once on the transition to solid Unknown
                    should_buzz = True
                    
            label = f"Unknown ({sim:.0%})"
            color = (0, 0, 255)
            lcd_show_for_label("Unknown", "ACCESS DENIED", "Unknown Person", auto_clear_sec=3, cooldown=5)
            if should_buzz:
                threading.Thread(target=red_alert, daemon=True).start()

    except Exception as e:
        print(f"[RECOG] worker error: {e}")
        label = "Error"
        color = (0, 0, 255)
        # LCD_ENABLED = False  # DO NOT CRASH LCD
    finally:
        with _labels_lock:
            if face_key in _face_labels and 'label' in locals():
                _face_labels[face_key]["label"] = label
                _face_labels[face_key]["color"] = color
        with _recog_lock:
            _recog_active.discard(face_key)


# -- Main thread: Display ----------------------------------------------------

def run():
    global _running

    init_db()
    # Nous avons retiré daily_reset() ici pour ne pas réinitialiser les présences au redémarrage en pleine journée
    
    lcd_init()

    print("[SYSTEM] Initializing face recognition...")
    initialize()
    
    # Start the Wi-Fi monitoring thread
    wifi_thread = threading.Thread(target=wifi_monitor_thread, daemon=True)
    wifi_thread.start()

    # Start the maintenance thread (daily reset & clean)
    maint_thread = threading.Thread(target=scheduled_maintenance_thread, daemon=True)
    maint_thread.start()

    camera = Camera()

    t1 = threading.Thread(target=camera_capture_thread, args=(camera,), daemon=True)
    t2 = threading.Thread(target=detection_thread, daemon=True)
    t1.start()
    t2.start()

    print("[SYSTEM] Waiting for camera...")
    while _latest_frame is None:
        time.sleep(0.05)

    print("[SYSTEM] Access system running. Press Q to stop. Press C to clear logs.\n")
    lcd_show("Access System", "Ready...")

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

        key = cv2.waitKey(5) & 0xFF
        if key == ord("q"):
            _running = False
            break
        elif key == ord("c"):
            print("\n[MANUAL] Triggering clear all logs...")
            clear_all_logs()
            lcd_show("Logs Cleared", "Database reset", 3)

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
