# convert_antspf.py
import torch
import os
import sys

BASE_DIR        = "/home/pi/Desktop/rasp"
SILENT_FACE_DIR = os.path.join(BASE_DIR, "Silent-Face-Anti-Spoofing-master")
OUTPUT_DIR      = os.path.join(BASE_DIR, "anti_spoof_models")

sys.path.insert(0, SILENT_FACE_DIR)
sys.path.insert(0, os.path.join(SILENT_FACE_DIR, "src"))

os.makedirs(OUTPUT_DIR, exist_ok=True)

from src.model_lib.MiniFASNet import MiniFASNetV1SE, MiniFASNetV2

MODELS = [
    {
        "name":   "MiniFASNetV2",
        "class":  MiniFASNetV2,
        "path":   os.path.join(SILENT_FACE_DIR,
                  "resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth"),
        "output": "MiniFASNetV2.onnx",
        "size":   80,
    },
    {
        "name":   "MiniFASNetV1SE",
        "class":  MiniFASNetV1SE,
        "path":   os.path.join(SILENT_FACE_DIR,
                  "resources/anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth"),
        "output": "MiniFASNetV1SE.onnx",
        "size":   80,
    }
]

for cfg in MODELS:
    print(f"\nConverting {cfg['name']}...")

    if not os.path.exists(cfg["path"]):
        print(f"  ❌ Not found: {cfg['path']}")
        continue

    model = cfg["class"](conv6_kernel=(5, 5))

    state = torch.load(cfg["path"], map_location="cpu")
    if "state_dict" in state:
        state = state["state_dict"]
    
    # Clean keys and dynamically map old SE layers to the new class structure
    cleaned_state = {}
    for k, v in state.items():
        k = k.replace("module.", "")            # Strip DataParallel prefix
        k = k.replace("se_fc", "se_module.fc")  # Fix Squeeze-and-Excitation FC naming
        k = k.replace("se_bn", "se_module.bn")  # Fix Squeeze-and-Excitation BN naming
        cleaned_state[k] = v

    # strict=False safely ignores trailing non-essential keys like num_batches_tracked
    model.load_state_dict(cleaned_state, strict=False)
    model.eval()

    dummy       = torch.randn(1, 3, cfg["size"], cfg["size"])
    output_path = os.path.join(OUTPUT_DIR, cfg["output"])

    torch.onnx.export(
        model,
        dummy,
        output_path,
        input_names         = ["input"],
        output_names        = ["output"],
        opset_version       = 11,
        do_constant_folding = True
    )

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  ✅ Saved: {cfg['output']} ({size_kb:.0f}KB)")

print("\n✅ All models converted successfully!")