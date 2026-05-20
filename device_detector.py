# device_detector.py
import cv2
import numpy as np
import onnxruntime as ort
import os

MODEL_PATH = "/home/pi/Desktop/rasp/yolov8n.onnx"
CONF_THRESHOLD = 0.15  
NMS_THRESHOLD = 0.45

_session = None
_input_name = None

def init_yolo():
    global _session, _input_name
    if _session is not None:
        return
    
    if not os.path.exists(MODEL_PATH):
        print(f"[YOLO] ❌ Model file not found at {MODEL_PATH}")
        return

    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4  # Scale smoothly across Pi multi-cores
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    _session = ort.InferenceSession(MODEL_PATH, sess_options=opts, providers=["CPUExecutionProvider"])
    _input_name = _session.get_inputs()[0].name
    print("[YOLO] ✅ Blazing-fast C++ Vectorized Detector Ready.")

def detect_spoof_devices(frame):
    """
    Scans the frame for laptops (63) or cell phones (67).
    Returns:
        bool: True if spoof device is found, False otherwise.
        list: Coordinates of detected devices [(x1, y1, x2, y2, class_id), ...]
    """
    global _session, _input_name
    if _session is None:
        init_yolo()

    orig_h, orig_w = frame.shape[:2]

    # ⚡ C++ OPTIMIZATION VECTOR: Replaces slow NumPy processing with atomic C++ code execution
    tensor = cv2.dnn.blobFromImage(
        frame, 
        scalefactor=1.0/255.0, 
        size=(320, 320), 
        swapRB=True, 
        crop=False
    )

    # Inference math
    outputs = _session.run(None, {_input_name: tensor})
    output = np.transpose(outputs[0][0])  # Shape: (2100, 84)

    boxes = output[:, :4]
    scores = output[:, 4:]
    class_ids = np.argmax(scores, axis=1)
    confidences = np.max(scores, axis=1)

    # Filter out everything except laptops (63) and phones (67)
    mask = (confidences > CONF_THRESHOLD) & (np.isin(class_ids, [63, 67]))
    
    valid_boxes = boxes[mask]
    valid_confs = confidences[mask]
    valid_ids = class_ids[mask]

    if len(valid_boxes) == 0:
        return False, []

    cv_boxes = []
    for box in valid_boxes:
        cx, cy, w, h = box
        x1 = int((cx - w / 2) * (orig_w / 320.0))
        y1 = int((cy - h / 2) * (orig_h / 320.0))
        box_w = int(w * (orig_w / 320.0))
        box_h = int(h * (orig_h / 320.0))
        cv_boxes.append([x1, y1, box_w, box_h])

    # 🛡️ NMS (Non-Maximum Suppression): Eliminates redundant duplicate boxes instantly 
    indices = cv2.dnn.NMSBoxes(cv_boxes, valid_confs.tolist(), CONF_THRESHOLD, NMS_THRESHOLD)
    
    spoof_boxes = []
    if len(indices) > 0:
        for idx in indices.flatten():
            x1, y1, box_w, box_h = cv_boxes[idx]
            x2 = x1 + box_w
            y2 = y1 + box_h
            spoof_boxes.append((x1, y1, x2, y2, int(valid_ids[idx])))
            
        return True, spoof_boxes

    return False, []