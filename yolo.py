import cv2

def main():
    from ultralytics import YOLO
    # Load the face detection model
    model = YOLO("yolov8n-face.pt")

    cap = cv2.VideoCapture(0)

    print("YOLO Face Detection running. Press Q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect faces
        results = model(frame, verbose=False)
        
        # Draw boxes automatically
        annotated = results[0].plot()

        cv2.imshow("YOLO Face Test", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()