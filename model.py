import cv2
import numpy as np
from collections import Counter
import traceback
from ultralytics import YOLO

# --- Configuration ---
# Point to your model file (Hugging Face link)
YOLO_MODEL_PATH = "https://huggingface.co/Devadiga04/best_Model/resolve/main/best_Model.pt"

# Global variable for lazy loading
model = None

def get_model():
    """
    Lazily loads the YOLO model only when required.
    This prevents Render from exceeding memory limits during startup.
    """
    global model
    if model is None:
        try:
            print("📦 Loading YOLO model (this may take a few seconds)...")
            model = YOLO(YOLO_MODEL_PATH)
            print("✅ YOLO model loaded successfully using the 'ultralytics' library.")
        except Exception as e:
            print(f"❌ CRITICAL ERROR: Failed to load YOLO model from '{YOLO_MODEL_PATH}'.")
            print(f"   Error: {e}")
            model = None
    return model


def predict_and_count_items(image_bytes: bytes) -> list:
    """
    Takes raw image bytes, runs them through the YOLO model,
    and returns a structured list of detected items and their counts.

    Args:
        image_bytes: Raw byte data of the JPEG image from the ESP32.

    Returns:
        A list of dictionaries, e.g., [{"type": "Tomato", "quantity": 15}, ...].
        Returns an empty list if the model isn't loaded or an error occurs.
    """
    try:
        model_instance = get_model()
        if model_instance is None:
            print("⚠️ Model is not loaded. Skipping prediction.")
            return []

        # Decode image bytes into an OpenCV image
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            print("⚠️ Failed to decode image. Check input format.")
            return []

        # Perform YOLO inference
        results = model_instance(img)
        detected_names = []

        # Access detected class names
        class_names = results[0].names

        for box in results[0].boxes:
            class_id = int(box.cls[0])
            item_name = class_names.get(class_id, "unknown")
            detected_names.append(item_name)

        # Count occurrences of each detected item
        ingredient_counts = Counter(detected_names)

        # Format the result
        formatted_ingredients = [
            {"type": ingredient.capitalize(), "quantity": count}
            for ingredient, count in ingredient_counts.items()
        ]

        print(f"✅ Detection complete. Found: {formatted_ingredients}")
        return formatted_ingredients

    except Exception as e:
        print(f"❌ ERROR during YOLO prediction process: {e}")
        traceback.print_exc()
        return []