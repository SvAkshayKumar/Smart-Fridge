import os
import cv2
import torch
import numpy as np
import requests
from collections import Counter
from ultralytics import YOLO
import traceback

# ================================
# CONFIGURATION
# ================================
# Replace with your own file ID from Google Drive
GOOGLE_DRIVE_FILE_ID = "1B_ISa9Bc_viTzhH9Rxa4e3wQUdPsD_PM"
MODEL_FILENAME = "best_Model.pt"
LOCAL_MODEL_PATH = os.path.join(os.getcwd(), MODEL_FILENAME)

# ================================
# DOWNLOAD MODEL FROM GOOGLE DRIVE
# ================================
def download_from_google_drive(file_id: str, destination: str) -> bool:
    """
    Downloads a file from Google Drive using its file ID.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(destination):
            print(f"✅ Model already exists locally at {destination}")
            return True

        print(f"⬇️  Downloading model from Google Drive (File ID: {file_id})...")

        # Direct download URL
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(url, stream=True)

        if response.status_code != 200:
            raise Exception(f"Google Drive download failed with status {response.status_code}")

        # Save the model
        with open(destination, "wb") as f:
            for chunk in response.iter_content(1024 * 1024):  # 1MB chunks
                f.write(chunk)

        print(f"✅ Model downloaded and saved to {destination}")
        return True

    except Exception as e:
        print(f"❌ ERROR downloading model from Google Drive: {e}")
        traceback.print_exc()
        return False


# ================================
# LOAD YOLO MODEL
# ================================
if download_from_google_drive(GOOGLE_DRIVE_FILE_ID, LOCAL_MODEL_PATH):
    try:
        model = YOLO(LOCAL_MODEL_PATH)
        print("✅ YOLO model loaded successfully.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Failed to load YOLO model. Error: {e}")
        model = None
else:
    model = None


# ================================
# PREDICTION FUNCTION
# ================================
def predict_and_count_items(image_bytes: bytes) -> list:
    """
    Takes raw image bytes, runs them through the loaded YOLO model,
    and returns a structured list of detected items and their counts.
    """
    if model is None:
        print("⚠️ Model not loaded — skipping prediction.")
        return []

    try:
        # Decode image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # Run inference
        results = model(img)
        class_names = results[0].names

        # Extract detections
        detected = [class_names[int(box.cls[0])] for box in results[0].boxes]

        # Count occurrences
        counts = Counter(detected)
        formatted = [{"type": k.capitalize(), "quantity": v} for k, v in counts.items()]

        print(f"✅ Detection complete: {formatted}")
        return formatted

    except Exception as e:
        print(f"❌ ERROR during YOLO prediction: {e}")
        traceback.print_exc()
        return []
