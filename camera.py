# camera.py
import cv2
import threading
from config import DEVICE, CAMERA_WIDTH, CAMERA_HEIGHT

class Camera:
    def __init__(self):
        self.cap = None
        self.picam = None
        
        # Threading variables
        self.ret = False
        self.frame = None
        self.running = True

        if DEVICE == "PI":
            from picamera2 import Picamera2
            self.picam = Picamera2()

            config = self.picam.create_preview_configuration(
                main={"size": (960, 720), "format": "BGR888"},
                
            )
            self.picam.configure(config)
            self.picam.set_controls({
                "FrameDurationLimits": (33333, 33333),
                "NoiseReductionMode":  0,
                "Sharpness":           1.0,
                
            })
            self.picam.start()
            print("[CAMERA] Pi Camera v2 ready (Threaded)")

        else:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            print("[CAMERA] USB Camera ready (Threaded)")

        # Start the background thread to constantly read frames
        self.thread = threading.Thread(target=self._update, args=())
        self.thread.daemon = True
        self.thread.start()

    def _update(self):
        # This runs constantly in the background
        while self.running:
            if DEVICE == "PI":
                raw_frame = self.picam.capture_array()
                raw_frame = cv2.cvtColor(raw_frame, cv2.COLOR_RGB2BGR)
                self.frame = cv2.resize(raw_frame, (CAMERA_WIDTH, CAMERA_HEIGHT))
                self.ret = True
            else:
                self.ret, self.frame = self.cap.read()

    def read(self):
        # Instantly return the most recent frame from the background thread
        return self.ret, self.frame

    def release(self):
        self.running = False
        self.thread.join() # Wait for thread to finish
        if DEVICE == "PI":
            self.picam.stop()
        else:
            self.cap.release()
