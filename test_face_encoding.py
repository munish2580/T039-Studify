import cv2
import numpy as np
import face_recognition
from PIL import Image

def test_encoding(image_path):
    # Load image with cv2
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load image: {image_path}")
        return
    # Convert BGR to RGB
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # Ensure contiguous array
    img_rgb = np.ascontiguousarray(img_rgb)
    print(f"Image shape: {img_rgb.shape}, dtype: {img_rgb.dtype}, contiguous: {img_rgb.flags.c_contiguous}")
    # Try face encoding
    try:
        encodings = face_recognition.face_encodings(img_rgb)
        print(f"Found {len(encodings)} face encodings")
    except Exception as e:
        print(f"Error during face encoding: {e}")

    # Alternative: convert to PIL and back to numpy
    pil_img = Image.fromarray(img_rgb)
    img_rgb_pil = np.array(pil_img)
    print(f"PIL converted image shape: {img_rgb_pil.shape}, dtype: {img_rgb_pil.dtype}, contiguous: {img_rgb_pil.flags.c_contiguous}")
    try:
        encodings_pil = face_recognition.face_encodings(img_rgb_pil)
        print(f"Found {len(encodings_pil)} face encodings after PIL conversion")
    except Exception as e:
        print(f"Error during face encoding after PIL conversion: {e}")

if __name__ == "__main__":
    test_encoding("student_images/Jaskaran_high_risk.jpg")
