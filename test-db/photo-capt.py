import cv2
import os

# Create folder for your photos
os.makedirs("test-db/Ahmed", exist_ok=True)

cap = cv2.VideoCapture(0)
count = 0

print("Press S to save a photo, Q to quit.")

while True:
    ret, frame = cap.read()
    cv2.imshow("Take Photos", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):
        count += 1
        path = f"test-db/Ahmed/photo_{count}.jpg"
        cv2.imwrite(path, frame)
        print(f"Photo {count} saved! ✅")

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()