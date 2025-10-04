# encode_faces.py (Test Version)
import cv2
import face_recognition
import pickle
import os
import numpy as np

folderPath = 'student_images'

# --- TEMPORARY CHANGE ---
# Comment out the original line that reads all files
# pathList = os.listdir(folderPath) 
# Add this line to only test the new image
pathList = ['test_face.jpg']
# --- END TEMPORARY CHANGE ---

print(f"Found files: {pathList}")

# (The rest of the file remains the same as the last version I provided)
# ...
imgList = []
studentUsernames = []

for path in pathList:
    # ... (rest of the code)