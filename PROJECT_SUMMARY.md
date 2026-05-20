# School Facial Recognition Access System — Project Summary
## For New Conversation Context

---

## Project Overview

A school facial recognition access system built with Python. Students are enrolled with face photos, and when they approach the door, the system recognizes them and logs entry/exit. Built for eventual deployment on Raspberry Pi.

---

## Developer Profile

- **Skill level:** Beginner learning Python while building
- **Learning style:** Line-by-line explanations with real-world analogies
- **OS:** Windows
- **IDE:** VS Code
- **Python:** 3.10.11 (venv310) — NOT 3.13 (incompatible with PyTorch)
- **GPU:** NVIDIA RTX 3050 Ti (not configured, using CPU for Pi compatibility)

---

## Project Location

```
C:\Users\user\Desktop\PFE-rec-fa\
```

---

## Virtual Environment

```
venv310\Scripts\activate  ← ALWAYS use this one
venv\  ← old Python 3.13, DO NOT USE
```

---

## Project File Structure

```
PFE-rec-fa/
├── main.py                          ← main access system
├── enroll.py                        ← student enrollment
├── database.py                      ← database functions
├── dashboard.py                     ← streamlit dashboard
├── anti_spoof.py                    ← anti-spoofing
├── logs.py                          ← log viewer
├── clear_logs.py                    ← log cleaner
├── students_db/                     ← student photos
│   └── john_doe/
│       ├── photo_1.jpg ... photo_30.jpg
│       └── representations_facenet.pkl (cache)
├── school_access.db                 ← SQLite database
├── yolov8n-face.pt                  ← YOLO face model
├── yolov8n.pt                       ← YOLO general model
├── Silent-Face-Anti-Spoofing-master/ ← anti-spoof library
│   ├── src/
│   ├── resources/
│   │   ├── anti_spoof_models/
│   │   │   ├── 2.7_80x80_MiniFASNetV2.pth
│   │   │   └── 4_0_0_80x80_MiniFASNetV1SE.pth
│   │   └── detection_model/
│   │       ├── deploy.prototxt
│   │       └── Widerface-RetinaFace.caffemodel
├── venv/                            ← Python 3.13 (DO NOT USE)
└── venv310/                         ← Python 3.10 (USE THIS)
```

---

## Installed Libraries (venv310)

```
opencv-python      4.13.0.92
deepface           0.0.98
ultralytics        8.4.18
streamlit          1.54.0
streamlit-autorefresh
torch              2.10+cpu
torchvision        0.25.0
tensorflow         2.20.0
tf-keras
sqlalchemy         2.0.47
numpy              2.4.2
pandas             2.3.3
```

---

## Completed Features

### 1. Student Enrollment (enroll.py)
- Opens camera with instructions per position
- 6 positions × 5 photos = 30 photos total
- Instructions: STRAIGHT, LEFT, RIGHT, UP, DOWN, SMILE
- Countdown between positions (3 seconds + 2 second delay)
- is_paused flag blocks photos during countdown
- PHOTO_DELAY = 2.0 seconds between photos
- ENROLL_FRAME_SKIP = 15 (YOLO every 15 frames)
- Progress bar on screen
- Next photo timer shown on screen
- Saves to students_db/name_folder/
- Adds student to database
- Deletes .pkl cache after enrollment

### 2. Face Recognition (main.py)
- YOLO detects faces (yolov8n-face.pt)
- DeepFace identifies person (Facenet model)
- Threading with Queue system (smooth camera)
- Frame skip = 30 (YOLO every 30 frames)
- Warmup function pre-loads DeepFace cache
- Entry/Exit tracking with 1-hour minimum duration
- Cooldown system (10 seconds between recognitions)
- face_labels{} stores names on screen
- Green box = known student
- Red box = unknown person

### 3. Database (database.py)
- SQLite database (school_access.db)
- SQLAlchemy ORM
- Tables: students, access_logs, attendance
- Functions: init_db, add_student, log_access,
  get_student_by_name, get_today_logs,
  get_attendance, daily_reset
- Threading lock (db_lock) prevents conflicts

### 4. Dashboard (dashboard.py)
- Streamlit web interface
- Access logs with filters (name, action, date)
- Attendance page with date selector
- Download CSV for any date
- Shows present/absent students
- Auto-refresh every 30 seconds

### 5. Anti-Spoofing (anti_spoof.py)
- Uses Silent-Face-Anti-Spoofing library
- Two AI models: MiniFASNetV1SE + MiniFASNetV2
- Per-face voting buffer (deque maxlen=10)
- REAL_THRESHOLD = 0.6 (60% votes must be REAL)
- SPOOF_FRAME_SKIP = 10
- POSITION_TOLERANCE = 80px (face tracking)
- Each face has independent buffer (key = center position)
- Orange = CHECKING, Green = REAL, Red = FAKE
- Works correctly for single face AND multiple faces simultaneously
- NOT yet integrated into main.py

---

## Key Configuration Values

### main.py
```python
STUDENTS_DB  = "students_db/"
THRESHOLD    = 0.5          # DeepFace distance threshold
FRAME_SKIP   = 30           # YOLO every 30 frames
COOLDOWN_SEC = 10           # seconds between recognitions
MODEL_NAME   = "Facenet"    # DeepFace model
```

### enroll.py
```python
ENROLL_FRAME_SKIP = 15      # YOLO every 15 frames
PHOTO_DELAY       = 2.0     # seconds between photos
num_photos        = 30      # total photos per student
```

### anti_spoof.py
```python
DEVICE_ID          = 0
SPOOF_FRAME_SKIP   = 10
BUFFER_SIZE        = 10
REAL_THRESHOLD     = 0.6
POSITION_TOLERANCE = 80
```

---

## Important Fixes Applied

### Python 3.13 → 3.10
- PyTorch incompatible with Python 3.13
- Created venv310 with Python 3.10.11
- All libraries reinstalled in venv310

### Silent-Face Path Fixes
- Added os.chdir(SILENT_FACE_PATH)
- Added sys.path.insert for src folder
- Fixed caffemodel relative path in anti_spoof_predict.py
- Changed crop_flag → crop (correct parameter name)

### Camera Lag Fixes
- Reduced resolution to 640x480
- Frame skip for YOLO
- Frame skip for anti-spoof
- Models loaded once at startup not every frame

### Enrollment Fixes
- is_paused flag prevents photos during countdown
- last_photo_time reset after countdown
- time.sleep(2) after countdown for positioning
- frame_counter reset after countdown

### Threading Fix
- Queue system for DeepFace (background thread)
- db_lock for database safety
- face_queue maxsize=1 prevents pileup

---

## Pending Features

### 1. Anti-Spoofing Integration into main.py
Logic:
```
YOLO detects face
        ↓
check_real_face() from anti_spoof.py
        ↓
FAKE → show "SPOOFING DETECTED" → deny access
REAL → send to DeepFace recognition
        ↓
Known → allow entry
Unknown → deny
```
Changes needed in main.py:
- Import check_real_face, get_stable_result,
  get_face_key, _face_buffers from anti_spoof
- Add spoof check before recognition queue
- Show red warning for fake faces

### 2. SMS/WhatsApp Notifications
- Send notification to parents when student arrives
- Libraries to consider: Twilio (SMS), pywhatkit (WhatsApp)
- Trigger: when student entry logged

### 3. Accuracy Improvements
- Re-enroll with 50 photos
- Switch to Facenet512 model
- Adjust threshold to 0.4
- Add face quality check (minimum size 60x60)
- Add brightness check

### 4. Raspberry Pi Deployment
- Hardware: Raspberry Pi 4 4GB
- Camera: HuskyLens (prototype) or Tapo C310 WiFi (final)
- Door control: 5V Relay + Electric Strike Lock
- Power: UPS Battery Backup
- Consider: Coral USB Accelerator for speed

---

## Files Fully Understood (Line by Line)

```
✅ main.py      — complete understanding
✅ enroll.py    — complete understanding
⬜ database.py  — not yet explained
⬜ dashboard.py — not yet explained
⬜ anti_spoof.py — partially explained (sections 1-4 done)
```

---

## How to Run Each File

```bash
# Activate environment first (ALWAYS)
venv310\Scripts\activate

# Run main access system
python main.py

# Run enrollment
python enroll.py

# Run dashboard
streamlit run dashboard.py

# Run anti-spoof test
python anti_spoof.py
```

---

## Important Notes for New Conversation

1. Always explain code line by line with real-world analogies
2. User is a beginner — avoid jargon without explanation
3. Always ask which part to explain before starting
4. Use section-by-section approach, wait for "yes" before continuing
5. User prefers complete code rewrites over partial fixes
6. User's terminal language is French (Windows in French)
7. Use venv310 — NOT venv
8. CPU only (no CUDA) for Pi compatibility
9. Project is called PFE (Final Year Project)
10. School is in Tunisia

---

## Next Session Starting Point

Continue with:
1. Finish explaining anti_spoof.py (sections 5 onwards)
2. Integrate anti-spoofing into main.py
3. SMS/WhatsApp notifications
4. Accuracy improvements
5. Raspberry Pi deployment preparation
