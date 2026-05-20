# main.py
# School facial recognition access system

import os
import cv2
from ultralytics import YOLO

from camera import Camera
from config import (
    BASE_DIR, FRAME_SKIP,
    GPIO_ENABLED, LED_GREEN, LED_RED, LED_YELLOW,
    BUZZER_PIN, UNLOCK_SECONDS
)
from face_db import initialize, recognize_face
from anti_spoof import check_real_face
from database1 import log_access, is_inside, update_inside, has_entry_today, has_exit_today, daily_reset, get_student_by_name
import time
import threading
import queue

# -- Hardware Setup ---------------------------------------------------------
LCD_ENABLED = True
LCD_ADDRESS = 0x27  # Change to 0x3F if needed

lcd            = None
_lcd_lock      = threading.Lock()
_lcd_queue     = queue.Queue()
_lcd_current   = ("", "")

def lcd_init():
    """Initialize LCD in its own thread to avoid blocking."""
    global lcd, LCD_ENABLED
    try:
        from RPLCD.i2c import CharLCD
        lcd = CharLCD(
            'PCF8574',
            LCD_ADDRESS,
            port=1,
            cols=16,
            rows=2,
            dotsize=8,
            charmap='A02',
            auto_linebreaks=False
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
    if not LCD_ENABLED:
        return
    _lcd_queue.put((line1[:16], line2[:16]))
    if auto_clear_sec > 0:
        def _reset():
            time.sleep(auto_clear_sec)
            _lcd_queue.put(("Access System", "Ready..."))
        threading.Thread(target=_reset, daemon=True).start()

# -- GPIO Setup -------------------------------------------------------------
_buzzer_pwm = None

if GPIO_ENABLED:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    for pin in [LED_GREEN, LED_RED, LED_YELLOW, BUZZER_PIN]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    # Initialiser le PWM du buzzer une seule fois au démarrage
    _buzzer_pwm = GPIO.PWM(BUZZER_PIN, 1000)
    print("[GPIO] GPIO ready")
else:
    print("[GPIO] PC mode -- GPIO disabled")

def green_flash():
    if not GPIO_ENABLED:
        print("[DOOR] Unlock (GPIO Disabled)")
        return
    try:
        import RPi.GPIO as GPIO
        GPIO.output(LED_GREEN, GPIO.HIGH)
        time.sleep(UNLOCK_SECONDS)
        GPIO.output(LED_GREEN, GPIO.LOW)
        print("[DOOR] Unlock (LED Green On)")
    except Exception as e:
        print(f"[DOOR] Error controlling LED: {e}")

_red_alert_lock = threading.Lock()

def red_alert():
    if not GPIO_ENABLED:
        print("[DOOR] Reject")
        return
        
    # Empêcher plusieurs threads de sonner en même temps
    if not _red_alert_lock.acquire(blocking=False):
        return
        
    try:
        import RPi.GPIO as GPIO
        GPIO.output(LED_RED, GPIO.HIGH)
        _buzzer_pwm.start(50)
        time.sleep(0.3)
        _buzzer_pwm.stop()
        time.sleep(1.7)
        GPIO.output(LED_RED, GPIO.LOW)
    finally:
        _red_alert_lock.release()

# -- Load YOLO --------------------------------------------------------------
print("[SYSTEM] Loading YOLO...")
model = YOLO(os.path.join(BASE_DIR, "yolov8n-face.pt"))
print("[SYSTEM] YOLO ready")

# -- State ------------------------------------------------------------------
face_labels = {}  # key: face index, value: {label, color, box}
_labels_lock = threading.Lock()

_spoof_cache = {}
DETECTION_DELAY = 15.0

# Variables pour le Thread IA
latest_frame = None
processing_active = True
tracked_faces = {}  # Cache du visage: { track_id: {'box': (x1,y1,x2,y2), 'name': ..., 'sim': ...} }
TRACKING_THRESHOLD = 50  # Pixels de tolérance pour le suivi

def calculate_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) // 2, (y1 + y2) // 2)

def distance(c1, c2):
    return ((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2) ** 0.5

def ai_worker():
    """Thread dédié à l'IA (Yolo + InsightFace + Anti-Spoof) pour ne pas bloquer la vidéo"""
    global latest_frame, processing_active, face_labels, tracked_faces, _spoof_cache
    
    last_unknown = 0
    frame_count = 0
    
    while processing_active:
        try:
            if latest_frame is None:
                time.sleep(0.01)
                continue
            
            # Ne traiter que 1 image sur FRAME_SKIP pour économiser le processeur du Raspberry
            frame_count += 1
            if frame_count % FRAME_SKIP != 0:
                time.sleep(0.01)
                continue
                
            # Copier la frame pour travailler dessus sans interférence
            frame = latest_frame.copy()
            
            # Réduire imgsz AU MAXIMUM (160) pour une détection éclair sur Raspberry Pi
            last_results = model(frame, imgsz=160, verbose=False)
            
            new_labels = {}
            new_tracked_faces = {}
            
            for r in last_results:
                for i, box in enumerate(r.boxes):
                    if float(box.conf[0]) < 0.40:
                        continue
                        
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    current_box = (x1, y1, x2, y2)
                    current_center = calculate_center(current_box)
                    
                    # -- VERIFIER LE CACHE (Solution 2) --
                    matched_name = None
                    matched_sim = 0.0
                    
                    for track_id, track_data in tracked_faces.items():
                        track_box = track_data['box']
                        track_center = calculate_center(track_box)
                        # Si le visage est à moins de TRACKING_THRESHOLD pixels de l'ancienne position
                        if distance(current_center, track_center) < TRACKING_THRESHOLD:
                            matched_name = track_data['name']
                            matched_sim = track_data['sim']
                            break
                            
                    if matched_name is None:
                        # Visage non trouvé dans le cache -> on l'ajoute avec statut temporaire
                        matched_name = "Detecting..."
                        matched_sim = 0.0
                        
                        # Lancer la reconnaissance lourde en arrière-plan pour ne pas geler YOLO
                        def background_recognize(bbox_to_rec, center_to_rec):
                            rec_name, rec_sim = recognize_face(frame.copy(), bbox_to_rec)
                            # Mettre à jour le suivi de façon asynchrone si le visage est toujours proche
                            for t_id, t_data in tracked_faces.items():
                                if distance(calculate_center(t_data['box']), center_to_rec) < TRACKING_THRESHOLD:
                                    t_data['name'] = rec_name
                                    t_data['sim'] = rec_sim
                                    break
                                    
                        threading.Thread(target=background_recognize, args=(current_box, current_center), daemon=True).start()
                    
                    # Mettre à jour le suivi
                    new_tracked_faces[i] = {
                        'box': current_box,
                        'name': matched_name,
                        'sim': matched_sim
                    }
                    
                    name = matched_name
                    sim = matched_sim
                    
                    # Ignorer la validation si on est encore en détection
                    if name == "Detecting...":
                        new_labels[i] = {"label": "Detecting...", "color": (255, 165, 0), "box": current_box}
                        continue

                    # -- RECONNAISSANCE SANS ANTI-SPOOF --
                    from config import SIMILARITY_THRESHOLD
                    display_sim = sim
                    if name != "Unknown" and sim >= SIMILARITY_THRESHOLD:
                        display_sim = 0.80 + ((sim - SIMILARITY_THRESHOLD) / (1.0 - SIMILARITY_THRESHOLD)) * 0.20

                    if name != "Unknown":
                        now = time.time()
                        cache_data = _spoof_cache.get(name, {'time': 0, 'text': ''})
                        cached_time = cache_data['time']
                        remaining_delay = int(DETECTION_DELAY - (now - cached_time))

                        if remaining_delay > 0:
                            status_text = cache_data.get('text', 'WAIT')
                            label = f"{name} ({display_sim:.0%}) | {status_text} | {remaining_delay}s"
                            color = (0, 255, 255) # yellow
                        else:
                            label = f"{name} ({display_sim:.0%})"
                            color = (0, 255, 0)    # green

                            # ---> VERIFICATION IMMEDIATE SANS ANTI-SPOOFING <---
                            _spoof_cache[name] = {'time': now, 'text': 'CHECKING'}
                            
                            def verify_and_unlock(verify_name, verify_frame, verify_box, verify_sim):
                                already_inside = is_inside(verify_name)
                                student = get_student_by_name(verify_name)
                                student_id = student.student_id if student else "UNKNOWN"
                                
                                if not already_inside:
                                    if has_entry_today(verify_name):
                                        print(f"[SYSTEM] 🚫 DENIED: {verify_name} already entered today.")
                                        lcd_show("Access Denied", "Already entered", auto_clear_sec=3)
                                        red_alert()
                                        _spoof_cache[verify_name] = {'time': time.time(), 'text': 'ALREADY IN'}
                                        return
                                        
                                    print(f"[SYSTEM] Allowed: {verify_name} (ENTRY) (Sim: {verify_sim:.0%})")
                                    log_access(student_id, verify_name, True, "ENTRY")
                                    update_inside(verify_name, True)
                                    lcd_show(f"Welcome {verify_name[:8]}", "ENTRY LOGGED", auto_clear_sec=4)
                                    green_flash()
                                    _spoof_cache[verify_name] = {'time': time.time(), 'text': 'ENTER'}
                                else:
                                    if has_exit_today(verify_name):
                                        print(f"[SYSTEM] 🚫 DENIED: {verify_name} already exited today.")
                                        lcd_show("Access Denied", "Already exited", auto_clear_sec=3)
                                        red_alert()
                                        _spoof_cache[verify_name] = {'time': time.time(), 'text': 'ALREADY OUT'}
                                        return
                                        
                                    print(f"[SYSTEM] Allowed: {verify_name} (EXIT) (Sim: {verify_sim:.0%})")
                                    log_access(student_id, verify_name, True, "EXIT")
                                    update_inside(verify_name, False)
                                    lcd_show(f"Goodbye {verify_name[:8]}", "EXIT LOGGED", auto_clear_sec=4)
                                    green_flash()
                                    _spoof_cache[verify_name] = {'time': time.time(), 'text': 'EXIT'}

                            # Lancer la vérification sans l'anti-fraude
                            threading.Thread(
                                target=verify_and_unlock,
                                args=(name, frame.copy(), current_box, display_sim),
                                daemon=True
                            ).start()

                    else:
                        label = "Unknown"
                        color = (0, 0, 255)    # red
                        if time.time() - last_unknown > 3:
                            lcd_show("ACCESS DENIED", "Unknown Person", auto_clear_sec=3)
                            threading.Thread(target=red_alert, daemon=True).start()
                            last_unknown = time.time()
                        
                    new_labels[i] = {"label": label, "color": color, "box": current_box}

            # Appliquer les résultats
            tracked_faces = new_tracked_faces
            with _labels_lock:
                face_labels = new_labels
        except Exception as e:
            import traceback
            print(f"[AI_WORKER] Crash détecté: {e}")
            traceback.print_exc()
            time.sleep(1)

# -- Main loop --------------------------------------------------------------

def run():
    global latest_frame, processing_active

    print("[SYSTEM] Performing daily reset (if needed)...")
    daily_reset()
    
    print("[SYSTEM] Initializing face recognition...")
    initialize()
    lcd_init()

    camera = Camera()

    print("[SYSTEM] 🟢 Access system running. Press Q to stop.\n")

    # DÉMARRAGE DU THREAD IA (Solution 1)
    threading.Thread(target=ai_worker, daemon=True).start()

    while True:
        ret, frame = camera.read()
        
        if not ret or frame is None:
            continue

        # Transmettre la frame actuelle au thread IA
        latest_frame = frame.copy()

        # Récupérer les labels sans bloquer
        with _labels_lock:
            current_labels = face_labels.copy()

        # -- Drawing (Happens every frame for smooth video at full FPS) --
        for i, info in current_labels.items():
            if "box" in info:
                color = info["color"]
                label = info["label"]
                x1, y1, x2, y2 = info["box"]

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(
                    frame, label,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, color, 2
                )
        
        supervision_path = os.path.join(BASE_DIR, "supervision.jpg")
        cv2.imwrite(supervision_path, frame)
        cv2.imshow("Access System", frame)
        
        if cv2.waitKey(1) & 0xFF == ord("q"):
            processing_active = False # Arrêter le thread proprement
            break

    camera.release()
    cv2.destroyAllWindows()
    print("[SYSTEM] System stopped.")


if __name__ == "__main__":
    run()
