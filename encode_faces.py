# encode_faces.py (Bypassing OpenCV)
import face_recognition
import pickle
import os

# Path to the directory where student images are stored
folderPath = 'student_images'
pathList = os.listdir(folderPath)
print(f"Found files: {pathList}")

encodeListKnown = []
studentUsernames = []

print("\nStarting encoding process using the direct loader...")
for path in pathList:
    username = os.path.splitext(path)[0]
    try:
        # Load the image file directly using face_recognition's built-in loader
        # This function handles all the necessary conversions automatically
        print(f"Processing image for '{username}'...")
        image = face_recognition.load_image_file(os.path.join(folderPath, path))
        
        # Get face encodings from the image
        encodings = face_recognition.face_encodings(image)
        
        if encodings:
            # Use the first face found in the image
            encodeListKnown.append(encodings[0])
            studentUsernames.append(username)
            print(f"--> Successfully encoded face for: '{username}'")
        else:
            print(f"Warning: No face was found in the image for '{username}'. Skipping.")

    except Exception as e:
        print(f"!!! An unexpected error occurred while processing '{username}': {e}")

# Save the data only if at least one face was successfully encoded
if encodeListKnown:
    encodeData = [studentUsernames, encodeListKnown]
    
    with open('EncodeFile.p', 'wb') as file:
        pickle.dump(encodeData, file)
    print("\nEncoding Complete. Face data saved to EncodeFile.p")
else:
    print("\nEncoding failed. No faces were successfully encoded.")