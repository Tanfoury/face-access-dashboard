# enroll.py
import cv2
import os
import time
import numpy as np
from database1 import init_db
from enrollment_sync import add_student_everywhere
from ultralytics import YOLO

# ---- PATH SETUP ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- LOAD YOLO ----
model = YOLO(os.path.join(BASE_DIR, "yolov8n-face.pt"))

# ---- CONFIG ----
ENROLL_FRAME_SKIP  = 15    # run YOLO every 15 frames only
PHOTO_DELAY        = 0.05  # seconds between each photo
MIN_FACE_SIZE      = 60    # minimum face width AND height in pixels
MIN_FACE_SIZE_FAR  = 30    # relaxed minimum for FAR position
MIN_SHARPNESS      = 60  # minimum sharpness score (higher = sharper)
MIN_SHARPNESS_STRAIGHT      = 100
MIN_BRIGHTNESS     = 40    # minimum brightness (0=black, 255=white)
MAX_BRIGHTNESS     = 220   # maximum brightness

# 25 photos limit / 5 positions = 5 photos per position
PHOTOS_PER_GROUP   = 5

# ---- INSTRUCTIONS ----
# Each entry: (instruction text, is_far_position)
INSTRUCTIONS = [
    ("Look STRAIGHT at camera",    False),
    ("Turn head slightly LEFT or RIGHT", False),
    ("Tilt head slightly UP",      False),
    ("SMILE naturally",            False),
    ("Move FAR from camera",       True),   # ← relaxed size check
]

def augment_and_save(img, index, save_dir):
    """
    Applique la solution 1 : Data Augmentation (Multiplie 1 photo par 5)
    Crée des variations artificielles pour maximiser la précision avec très peu de prises.
    """
    # 1. Original
    cv2.imwrite(f"{save_dir}/photo_{index}_orig.jpg", img)
    
    # 2. Miroir (Inversion horizontale)
    flipped = cv2.flip(img, 1)
    cv2.imwrite(f"{save_dir}/photo_{index}_flip.jpg", flipped)
    
    # 3. Luminosité augmentée
    bright = cv2.convertScaleAbs(img, alpha=1.2, beta=30)
    cv2.imwrite(f"{save_dir}/photo_{index}_bright.jpg", bright)
    
    # 4. Luminosité diminuée
    dark = cv2.convertScaleAbs(img, alpha=0.8, beta=-30)
    cv2.imwrite(f"{save_dir}/photo_{index}_dark.jpg", dark)
    
    # 5. Léger Flou (Simule un mouvement ou mauvais autofocus)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    cv2.imwrite(f"{save_dir}/photo_{index}_blur.jpg", blur)


# ---- QUALITY CHECK FUNCTION ----
def check_quality(face, is_far=False, is_straight=False):
    """
    Checks if face photo is good enough to save.
    is_far:      relaxed size check for FAR position
    is_straight: stricter sharpness for STRAIGHT position
    Returns: is_good (bool), reason (str)
    """
    h, w = face.shape[:2]

    # ---- CHECK 1: Face size ----
    min_size = MIN_FACE_SIZE_FAR if is_far else MIN_FACE_SIZE
    if w < min_size or h < min_size:
        return False, "Too small - move closer!"

    # ---- CHECK 2: Sharpness ----
    gray      = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    # stricter when looking straight, relaxed for angles
    threshold = MIN_SHARPNESS_STRAIGHT if is_straight else MIN_SHARPNESS
    if sharpness < threshold:
        return False, "Too blurry - hold still!"

    # ---- CHECK 3: Brightness ----
    brightness = face.mean()
    if brightness < MIN_BRIGHTNESS:
        return False, "Too dark - need more light!"
    if brightness > MAX_BRIGHTNESS:
        return False, "Too bright - less light!"

    return True, "OK"


def enroll_student(name, student_id, grade, category, num_photos=25):

    # create student folder
    folder_name = name.replace(" ", "_").lower()
    save_dir    = os.path.join(BASE_DIR, f"students_db/{folder_name}")
    os.makedirs(save_dir, exist_ok=True)

    # open camera using the central Camera class (supports Pi Camera)
    from camera import Camera
    cap = Camera()

    if not cap.running:
        print("[ERROR] Cannot open camera!")
        return

    # Wait for camera to warm up and capture the first frame
    print("[ENROLL] Waiting for camera to warm up...")
    timeout = 10
    start_time = time.time()
    while not cap.ret:
        if time.time() - start_time > timeout:
            print("[ERROR] Camera timeout - no frames received!")
            return
        time.sleep(0.1)

    count           = 0
    last_group      = -1
    frame_counter   = 0
    last_photo_time = 0
    is_paused       = False
    reject_reason   = ""      # stores why last photo was rejected
    reject_timer    = 0       # how long to show rejection message

    print(f"\n[ENROLL] Starting for: {name}")
    print(f"[ENROLL] Target: {num_photos} photos")
    print(f"[ENROLL] Press Q to quit\n")

    while count < num_photos:

        # ---- READ FRAME ----
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Cannot read frame!")
            break

        frame_counter += 1
        h, w = frame.shape[:2]

        # ---- CURRENT INSTRUCTION ----
        # 50 photos ÷ 7 positions = ~7 photos per position
        current_group          = min(count // PHOTOS_PER_GROUP, len(INSTRUCTIONS) - 1)
        instruction, is_far    = INSTRUCTIONS[current_group]

        # ---- PAUSE BETWEEN GROUPS ----
        if current_group != last_group and count != 0:
            last_group = current_group
            is_paused  = True
            time.sleep(0.5)

            for countdown in range(3, 0, -1):
                ret, frame = cap.read()
                if not ret:
                    break

                h, w = frame.shape[:2]

                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

                cv2.putText(frame, str(countdown),
                    (w // 2 - 40, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 4,
                    (0, 255, 255), 5)

                cv2.putText(frame, f"Next: {instruction}",
                    (w // 2 - 180, h // 2 + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 255), 2)

                cv2.putText(frame,
                    "Get ready for next position...",
                    (w // 2 - 220, h // 2 + 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 255), 2)

                cv2.imshow("Enrollment", frame)
                cv2.waitKey(1000)

            time.sleep(2)
            frame_counter   = 0
            last_photo_time = time.time()
            is_paused       = False
            reject_reason   = ""

        last_group = current_group

        # ---- DRAW TOP BAR ----
        cv2.rectangle(frame, (0, 0), (w, 90), (0, 0, 0), -1)

        cv2.putText(frame, instruction,
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9,
            (0, 255, 255), 2)

        cv2.putText(frame, f"Photos: {count}/{num_photos}",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (255, 255, 255), 2)

        # ---- PROGRESS BAR ----
        bar_w  = w - 40
        filled = int(bar_w * count / num_photos)
        cv2.rectangle(frame, (20, 75), (w - 20, 88), (50, 50, 50), -1)
        if filled > 0:
            cv2.rectangle(frame, (20, 75), (20 + filled, 88), (0, 255, 0), -1)

        # ---- RUN YOLO EVERY 15 FRAMES ONLY ----
        face_detected = False

        if frame_counter % ENROLL_FRAME_SKIP == 0 and not is_paused:
            now = time.time()

            if now - last_photo_time >= PHOTO_DELAY:

                results = model(frame, verbose=False)

                for result in results:
                    for box in result.boxes:
                        conf = float(box.conf[0])
                        if conf < 0.5:
                            continue

                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        pad = 20
                        x1  = max(0, x1 - pad)
                        y1  = max(0, y1 - pad)
                        x2  = min(w, x2 + pad)
                        y2  = min(h, y2 + pad)

                        face = frame[y1:y2, x1:x2]

                        if face.size == 0:
                            continue

                        # ---- QUALITY CHECK ----
                        is_straight = (current_group == 0)  # first position = STRAIGHT
                        is_good, reason = check_quality(face, is_far=is_far, is_straight=is_straight)

                        if not is_good:
                            # photo rejected — show reason
                            reject_reason = reason
                            reject_timer  = time.time()
                            print(f"  ⚠️  Rejected: {reason}")

                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
                            cv2.putText(frame, reason,
                                (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                                (0, 165, 255), 2)
                            continue

                        # ---- PHOTO ACCEPTED ----
                        clean_frame = frame[90:, :]
                        count += 1
                        
                        # --- SOLUTION 1: DATA AUGMENTATION SUR LE CHAMP ---
                        # Prends 1 capture et l'enregistre en 5 versions artificielles
                        augment_and_save(clean_frame, count, save_dir)
                        
                        face_detected   = True
                        last_photo_time = now
                        reject_reason   = ""
                        print(f"  📸 {count}/{num_photos} — {instruction} (Augmentée x5)")

                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, "✓ Captured!",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0), 2)

        # ---- SHOW REJECTION REASON FOR 2 SECONDS ----
        if reject_reason and time.time() - reject_timer < 2.0:
            cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 0), -1)
            cv2.putText(frame, f"⚠ {reject_reason}",
                (20, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 165, 255), 2)
        else:
            reject_reason = ""

        # ---- NO FACE WARNING ----
        if not face_detected and frame_counter % ENROLL_FRAME_SKIP == 0 and not reject_reason:
            cv2.putText(frame,
                "No face detected - move closer!",
                (w // 2 - 200, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 255), 2)

        # ---- NEXT PHOTO TIMER ----
        time_since_last = time.time() - last_photo_time
        time_until_next = max(0, PHOTO_DELAY - time_since_last)

        if time_until_next > 0 and count > 0:
            cv2.putText(frame,
                f"Next photo in: {time_until_next:.1f}s",
                (w - 250, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                (255, 255, 0), 2)

        # ---- ALWAYS SHOW WINDOW ----
        cv2.imshow("Enrollment", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n[ENROLL] Cancelled.")
            break

    # ---- CLEANUP ----
    cap.release()
    cv2.destroyAllWindows()

    # ---- SAVE TO DATABASE ----
    if count > 0:
        name = name.strip().title()
        add_student_everywhere(name, student_id, grade, save_dir, category)

       # ---- EXTRACT FACE VECTORS WITH INSIGHTFACE ----
        print(f"\n[ENROLL] 🔄 Extracting face vectors...")
        from face_db import enroll_face
        success = enroll_face(name, save_dir)
        if success:
            print(f"[ENROLL] ✅ Face vectors saved for {name}")
        else:
            print(f"[ENROLL] ⚠️  Vector extraction failed — re-enroll if recognition fails")

        # delete old DeepFace cache if exists
        for f in os.listdir(save_dir):
            if f.endswith(".pkl"):
                os.remove(os.path.join(save_dir, f))

        print(f"\n[ENROLL] ✅ Done! {count} photos saved for {name}")
        print(f"[ENROLL] 📁 Saved to: {save_dir}")
    else:
        print("[ENROLL] ❌ No photos captured.")


def enroll_from_folder(name, student_id, grade, category, source_folder):
    """
    Inscrit un étudiant en important des photos existantes d'un dossier.
    Applique automatiquement l'augmentation de données.
    """
    if not os.path.exists(source_folder):
        print(f"[ENROLL] ❌ Error: Folder '{source_folder}' not found.")
        return

    folder_name = name.replace(" ", "_").lower()
    save_dir    = os.path.join(BASE_DIR, f"students_db/{folder_name}")
    os.makedirs(save_dir, exist_ok=True)

    count = 0
    valid_extensions = (".jpg", ".jpeg", ".png")
    
    print(f"\n[ENROLL] Importing photos from {source_folder}...")
    
    for file_name in os.listdir(source_folder):
        if file_name.lower().endswith(valid_extensions):
            img_path = os.path.join(source_folder, file_name)
            img = cv2.imread(img_path)
            if img is not None:
                count += 1
                # On applique la data augmentation comme avec la caméra
                augment_and_save(img, count, save_dir)
                print(f"  📸 Imported {file_name} (Augmentée x5)")

    if count == 0:
        print("[ENROLL] ❌ No valid photos found in the folder.")
        return

    name = name.strip().title()

    # ---- SAVE TO DATABASE ----
    add_student_everywhere(name, student_id, grade, save_dir, category)

    # ---- EXTRACT FACE VECTORS WITH INSIGHTFACE ----
    print(f"\n[ENROLL] 🔄 Extracting face vectors...")
    from face_db import enroll_face
    success = enroll_face(name, save_dir)
    if success:
        print(f"[ENROLL] ✅ Face vectors saved for {name}")
    else:
        print(f"[ENROLL] ⚠️  Vector extraction failed — re-enroll if recognition fails")

    print(f"\n[ENROLL] ✅ Done! {count} original photos imported and augmented for {name}")
    print(f"[ENROLL] 📁 Saved to: {save_dir}")


# ---- RUN ----
if __name__ == "__main__":
    init_db()

    print("=== STUDENT ENROLLMENT ===")
    name       = input("Full Name     : ")
    student_id = input("ID            : ")
    category   = input("Category (eleve/prof/admin) [défaut: eleve] : ") or "eleve"
    grade      = input("Grade / Class : ")

    print("\nChoix de la méthode d'inscription :")
    print("[1] Capturer 25 photos avec la Caméra")
    print("[2] Importer des photos depuis un dossier existant")
    
    choice = input("Votre choix (1/2) : ").strip()
    
    if choice == "2":
        source_folder = input("Entrez le chemin complet du dossier contenant les photos : ").strip()
        enroll_from_folder(name, student_id, grade, category, source_folder)
    else:
        enroll_student(name, student_id, grade, category)