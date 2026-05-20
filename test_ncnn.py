def main():
	from ultralytics import YOLO

	# Load stock lightweight Nano weights (knows people, phones, laptops)
	model = YOLO("yolov8n.pt")

	# Export to ONNX format at 320x320 for high performance on Pi CPU
	model.export(format="onnx", imgsz=320)
	print("✅ Optimized yolov8n.onnx created successfully!")

if __name__ == '__main__':
	main()