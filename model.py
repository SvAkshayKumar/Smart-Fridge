import cv2
import torch
import numpy as np
from collections import Counter
import traceback
from ultralytics import YOLO

# --- Configuration ---
# ACTION REQUIRED: Ensure this path points to your actual model file.
# Using a raw string (r"...") is a good practice for Windows paths to avoid issues with backslashes.
YOLO_MODEL_PATH = r"best_Model.pt"

# --- Load the YOLO Model ---
# This block runs once when the application starts, loading the model into memory.
try:
    # Use the ultralytics YOLO class to load your custom-trained model.
    model = YOLO(YOLO_MODEL_PATH)
    print("✅ YOLO model loaded successfully using the 'ultralytics' library.")
except Exception as e:
    print(f"❌ CRITICAL ERROR: Failed to load YOLO model from '{YOLO_MODEL_PATH}'.")
    print(f"   Error: {e}")
    print("   Please ensure the path is correct and the 'ultralytics' library is installed (`pip install ultralytics`).")
    # Set model to None so the app can still run, but prediction will be disabled.
    model = None

def predict_and_count_items(image_bytes: bytes) -> list:
    """
    Takes raw image bytes, runs them through the loaded YOLO model,
    and returns a structured list of detected items and their counts.

    Args:
        image_bytes: The raw byte data of the JPEG image from the ESP32.

    Returns:
        A list of dictionaries, e.g., [{"type": "Tomato", "quantity": 15}, ...].
        Returns an empty list if the model isn't loaded or an error occurs.
    """
    if model is None:
        print("⚠️ Model is not loaded. Skipping prediction.")
        return []

    try:
        # 1. Decode the image
        # Convert the raw image bytes into a NumPy array.
        np_arr = np.frombuffer(image_bytes, np.uint8)
        # Decode the NumPy array into a color image format (BGR) that OpenCV can use.
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # 2. Perform inference
        # The model directly takes the image and returns a list of result objects.
        results = model(img)

        # --- 3. Process Results (CORRECTED METHOD) ---
        # The '.pandas()' method is from older versions. The new 'results' object is handled differently.
        detected_names = []
        
        # The result object contains the names map (e.g., {0: 'apple', 1: 'tomato'})
        class_names = results[0].names 
        
        # Iterate through all detected boxes in the first result.
        for box in results[0].boxes:
            # Get the class index (e.g., 0, 1) and convert it to an integer.
            class_id = int(box.cls[0])
            # Use the class index to look up the class name (e.g., 'apple').
            item_name = class_names[class_id]
            detected_names.append(item_name)
        
        # 4. Count and Format the Output
        # Use the Counter utility to efficiently count occurrences of each item.
        # e.g., ['tomato', 'tomato', 'apple'] -> {'tomato': 2, 'apple': 1}
        ingredient_counts = Counter(detected_names)

        # Format the counted items into the JSON structure required by app.py.
        formatted_ingredients = [
            {"type": ingredient.capitalize(), "quantity": count} 
            for ingredient, count in ingredient_counts.items()
        ]

        print(f"✅ Detection complete. Found: {formatted_ingredients}")
        return formatted_ingredients

    except Exception as e:
        print(f"❌ ERROR during YOLO prediction process: {e}")
        traceback.print_exc()
        # Return an empty list to prevent the main app from crashing.
        return []