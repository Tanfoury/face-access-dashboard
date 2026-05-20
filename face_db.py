# face_db.py
# InsightFace ArcFace recognition + FAISS vector search

import os
import cv2
import faiss
import pickle
import numpy as np
from insightface.app import FaceAnalysis

from config import INSIGHTFACE_MODEL, SIMILARITY_THRESHOLD

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
VECTORS_PATH = os.path.join(BASE_DIR, "students_db", "face_vectors.pkl")

_app           = None
_index         = None
_student_names = []


# ── Load InsightFace model ──────────────────────────────────────────────────

def load_model():
    global _app

    if _app is not None:
        return

    print(f"[FACE_DB] Loading InsightFace model: {INSIGHTFACE_MODEL}...")
    _app = FaceAnalysis(
        name            = INSIGHTFACE_MODEL,
        root            = BASE_DIR,  # Force le dossier du projet pour le raspberry pi
        allowed_modules = ["detection", "recognition"],
        providers       = ["CPUExecutionProvider"]
    )
    _app.prepare(ctx_id=-1, det_size=(320, 320))
    print("[FACE_DB] ✅ InsightFace model ready!")


# ── Extract 512-number vector from image ───────────────────────────────────

def extract_vector(img):
    """
    Takes a BGR image.
    Returns normalized 512-float vector, or None if no face found.
    """
    global _app

    if _app is None:
        load_model()

    try:
        faces = _app.get(img)

        if not faces:
            return None

        # use largest face if multiple detected
        largest = max(
            faces,
            key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
        )
        return largest.normed_embedding.astype(np.float32)

    except Exception as e:
        print(f"[FACE_DB] extract_vector error: {e}")
        return None


# ── Vector storage ─────────────────────────────────────────────────────────

def load_vectors():
    if os.path.exists(VECTORS_PATH):
        with open(VECTORS_PATH, "rb") as f:
            return pickle.load(f)
    return {}


def save_vectors(data):
    os.makedirs(os.path.dirname(VECTORS_PATH), exist_ok=True)

    # backup before saving
    if os.path.exists(VECTORS_PATH):
        import shutil
        shutil.copy2(VECTORS_PATH, VECTORS_PATH.replace(".pkl", "_backup.pkl"))

    with open(VECTORS_PATH, "wb") as f:
        pickle.dump(data, f)


# ── Build FAISS index ───────────────────────────────────────────────────────

def build_index():
    global _index, _student_names

    data = load_vectors()

    if not data:
        _index         = None
        _student_names = []
        print("[FACE_DB] ⚠️ No students enrolled yet")
        return

    _student_names = list(data.keys())
    matrix         = np.array(list(data.values()), dtype=np.float32)

    _index = faiss.IndexFlatIP(matrix.shape[1])
    _index.add(matrix)

    print(f"[FACE_DB] ✅ FAISS index built — {len(_student_names)} students")


# ── Recognize face ─────────────────────────────────────────────────────────

def recognize_face(img, bbox=None):
    """
    Identifies a face in the image.
    img:  full BGR frame from camera
    bbox: (x1,y1,x2,y2) bounding box from YOLO
    Returns: (name, similarity)
    """
    global _index, _student_names

    if _index is None or len(_student_names) == 0:
        return "Unknown", 0.0

    # crop face region with padding
    if bbox is not None:
        x1, y1, x2, y2 = bbox
        h, w = img.shape[:2]
        pad  = 40
        x1   = max(0, x1 - pad)
        y1   = max(0, y1 - pad)
        x2   = min(w, x2 + pad)
        y2   = min(h, y2 + pad)
        img  = img[y1:y2, x1:x2]

        if img.size == 0:
            return "Unknown", 0.0

        # Forcer une petite taille fixe pour accélérer drastiquement InsightFace sur le Raspberry Pi
        # (Sinon si le visage est près, l'image est grande et l'IA rame énormément)
        img = cv2.resize(img, (128, 128))

    # extract vector
    vector = extract_vector(img)

    if vector is None:
        print("[FACE_DB] ⚠️ No face detected in crop")
        return "Unknown", 0.0

    # normalize
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    # FAISS search
    D, I       = _index.search(vector.reshape(1, -1), k=1)
    similarity = float(D[0][0])
    idx        = int(I[0][0])
    name       = _student_names[idx]

    print(f"[FACE_DB] Best match: {name} — similarity: {similarity:.2f}")

    if similarity >= SIMILARITY_THRESHOLD:
        # progressive learning in background thread
        import threading
        threading.Thread(
            target = _update_vector,
            args   = (name, vector, similarity),
            daemon = True
        ).start()
        return name, round(similarity, 2)

    return "Unknown", round(similarity, 2)


# ── Progressive learning ────────────────────────────────────────────────────

def _update_vector(name, new_vector, similarity):
    """
    Silently updates stored vector toward new capture.
    Only when similarity is confident (0.70 - 0.98).
    Runs in background thread — zero delay to door.
    """
    if similarity < 0.70 or similarity > 0.98:
        return

    try:
        all_vectors   = load_vectors()
        if name not in all_vectors:
            return

        learning_rate = 0.10
        old_vector    = all_vectors[name]
        updated       = (1 - learning_rate) * old_vector + learning_rate * new_vector
        norm          = np.linalg.norm(updated)
        if norm > 0:
            updated = updated / norm

        all_vectors[name] = updated.astype(np.float32)
        save_vectors(all_vectors)
        build_index()

        print(f"[FACE_DB]  {name} vector updated (similarity: {similarity:.2f})")

    except Exception as e:
        print(f"[FACE_DB] update error: {e}")


# ── Enroll face ─────────────────────────────────────────────────────────────

def enroll_face(name, photos_folder):
    """
    Processes all photos in folder, averages vectors, saves master vector.
    """
    all_vectors = load_vectors()
    vectors     = []

    photos = sorted([
        f for f in os.listdir(photos_folder)
        if f.lower().endswith((".jpg", ".png"))
    ])

    print(f"[FACE_DB] Processing {len(photos)} photos for {name}...")

    for photo in photos:
        img = cv2.imread(os.path.join(photos_folder, photo))
        if img is None:
            continue
        vector = extract_vector(img)
        if vector is not None:
            vectors.append(vector)

    if not vectors:
        print(f"[FACE_DB] ❌ No valid faces found for {name}")
        return False

    master = np.mean(vectors, axis=0)
    norm   = np.linalg.norm(master)
    if norm > 0:
        master = master / norm

    all_vectors[name] = master.astype(np.float32)
    save_vectors(all_vectors)
    build_index()

    print(f"[FACE_DB] ✅ {name} enrolled — {len(vectors)}/{len(photos)} photos used")
    return True


# ── Initialize ──────────────────────────────────────────────────────────────

def initialize():
    load_model()
    build_index()
    print("[FACE_DB] ✅ Face database ready!")
