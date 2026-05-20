# anti_spf.py
import cv2
import numpy as np
import onnxruntime as ort
import os
from collections import deque

BASE_DIR   = "/home/pi/Desktop/rasp"
MODEL_PATH = os.path.join(BASE_DIR, "anti_spoof_models", "MiniFASNetV2.onnx")

# ── Config ──────────────────────────────────────────────────────────────────
REAL_THRESHOLD = 0.70  
MIN_VOTES      = 5     
INPUT_SIZE     = (80, 80)
  # 2.7 for MiniFASNetV2 | 4.0 for MiniFASNetV1SE

# ── Session ─────────────────────────────────────────────────────────────────
_session    = None
_input_name = None

def initialize():
    global _session, _input_name
    if _session is not None:
        return

    if not os.path.exists(MODEL_PATH):
        print(f"[SPOOF] ❌ Model not found at: {MODEL_PATH}")
        return

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    _session = ort.InferenceSession(
        MODEL_PATH,
        sess_options=opts,
        providers=["CPUExecutionProvider"]
    )
    _input_name = _session.get_inputs()[0].name
    print(f"[SPOOF] ✅ Anti-spoof model loaded: {os.path.basename(MODEL_PATH)}")

def check_frame(face_crop):
    global _session, _input_name
    if _session is None:
        return False, 0.0

    try:
        # 1. Resize crop area to the model's required input dimensions
        img = cv2.resize(face_crop, INPUT_SIZE)
        
        # 2. CRITICAL FIX: Convert BGR (OpenCV default) to RGB (Model training default)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # 3. Scale pixel values to floating points between [0.0, 1.0]
        img = img.astype(np.float32) / 255.0
        
        # 4. Transpose from HWC (Height, Width, Channels) to CHW (Channels, Height, Width)
        img = np.transpose(img, (2, 0, 1))
        
        # 5. Add batch dimension -> result shape is exactly (1, 3, 80, 80)
        tensor = np.expand_dims(img, axis=0)

        # 6. Execute model inference
        outputs = _session.run(None, {_input_name: tensor})
        
        # 7. CRITICAL FIX: Safely parse raw outputs without flattening array shapes
        raw_outputs = outputs[0]  # Shape remains (1, 3)
        
        # Compute Softmax across rows
        exp_out = np.exp(raw_outputs - np.max(raw_outputs, axis=1, keepdims=True))
        probs   = exp_out / exp_out.sum(axis=1, keepdims=True)
        
        # Extract the real face confidence score safely using 2D mapping
        real_score = float(probs[0][1]) 
        is_real    = real_score >= REAL_THRESHOLD

        return is_real, real_score

    except Exception as e:
        # If something crashes behind the scenes, we can now see it in the terminal
        print(f"[SPOOF] Inference pipeline exception error: {e}")
        return False, 0.0

# ── Voting buffer ────────────────────────────────────────────────────────────
class SpoofBuffer:
    def __init__(self):
        self.buffer = deque(maxlen=10)
        self.result = "CHECKING"

    def add_vote(self, is_real, confidence):
        self.buffer.append(is_real)
        if len(self.buffer) < MIN_VOTES:
            self.result = "CHECKING"
            return

        real_votes = sum(self.buffer)
        ratio      = real_votes / len(self.buffer)
        self.result = "REAL" if ratio >= 0.55 else "FAKE"

    def get_result(self):
        return self.result

_buffers = {}

def get_buffer(face_key):
    if face_key not in _buffers:
        _buffers[face_key] = SpoofBuffer()
    return _buffers[face_key]