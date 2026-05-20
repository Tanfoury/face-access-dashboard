# config.py
import os

DEVICE   = "PI"  # "PC" or "PI"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if DEVICE == "PI":
    CAMERA_WIDTH        = 640
    CAMERA_HEIGHT       = 480
    FRAME_SKIP          = 3
    SPOOF_FRAME_SKIP    = 30
    INSIGHTFACE_MODEL   = "buffalo_s"
    USE_VULKAN          = False
    INFERENCE_BACKEND   = "onnx"
    GPIO_ENABLED        = True
    LCD_PIN             = 18
    LED_GREEN           = 27
    LED_RED             = 22
    LED_YELLOW          = 17
    BUZZER_PIN          = 23
    ANTI_DOUBLE_DELAY   = 60  # seconds
    UNLOCK_SECONDS      = 3
    SIMILARITY_THRESHOLD = 0.35

else:  # PC
    CAMERA_WIDTH        = 640
    CAMERA_HEIGHT       = 480
    FRAME_SKIP          = 5
    SPOOF_FRAME_SKIP    = 5
    INSIGHTFACE_MODEL   = "buffalo_l"
    USE_VULKAN          = False
    INFERENCE_BACKEND   = "onnx"
    GPIO_ENABLED        = False
    RELAY_PIN           = None
    UNLOCK_SECONDS      = 3
    SIMILARITY_THRESHOLD = 0.5
