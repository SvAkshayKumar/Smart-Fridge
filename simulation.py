# Import necessary libraries
import requests # This line is crucial for making HTTP requests
import json
import random
import io

# --- Configuration ---
# Ensure this IP address is correct for the machine running your Flask server
SERVER_URL = "http://10.186.2.170:5000/newdata" 

# --- ACTION REQUIRED: EDIT THIS LINE ---
# Change this to the exact filename of the image in the same folder.
IMAGE_FILE_PATH = "capture_20251024_235016.jpg"
# For example: IMAGE_FILE_PATH = "my_fridge_photo.jpg"
# --------------------------------------

# --- Helper Functions ---

def load_image_from_file(filepath):
    """
    Opens a specified image file in binary mode and returns its raw byte data.
    This simulates the ESP32 sending its camera buffer.
    """
    try:
        with open(filepath, 'rb') as f:
            image_bytes = f.read()
        print(f"Successfully loaded image '{filepath}' ({len(image_bytes)} bytes).")
        return image_bytes
    except FileNotFoundError:
        print(f"❌ CRITICAL ERROR: The image file was not found at '{filepath}'.")
        print("   Please make sure the file exists and 'IMAGE_FILE_PATH' is correct.")
        return None
    except Exception as e:
        print(f"❌ CRITICAL ERROR: An unexpected error occurred while reading the image file: {e}")
        return None

def generate_sample_inventory():
    """
    Creates a randomized list of items to simulate a fridge inventory.
    The structure {"items": [...]} matches what the server expects.
    """
    possible_items = [
        "Tomato", "Apple","Eggs","Onion","Yogurt"
    ]
    num_items = random.randint(0,4)
    selected_items = random.sample(possible_items, num_items)
    inventory_list = []
    for item_name in selected_items:
        quantity = random.randint(1,2) if item_name != "Milk" else 1
        inventory_list.append({"type": item_name, "quantity": quantity})
    
    # This format is exactly what the server's X-Metadata header expects
    metadata_object = {"items": inventory_list}
    return json.dumps(metadata_object)

# --- Main Simulation Logic ---

def run_simulation():
    """
    Main function to prepare and send the simulated data to your Flask server.
    """
    print("--- ESP32 Simulation Started (using local image) ---")
    
    # 1. Load the image from the specified file
    image_bytes = load_image_from_file(IMAGE_FILE_PATH)
    if image_bytes is None:
        print("Aborting simulation due to image loading error.")
        return

    # 2. Generate the sample inventory JSON string
    inventory_json_string = generate_sample_inventory()
    print(f"Generated Inventory: {inventory_json_string}")
    
    # 3. Prepare the HTTP request headers.
    # The server reads the inventory from 'X-Metadata'.
    headers = {
        'X-Metadata': inventory_json_string,
        'Content-Type': 'image/jpeg'
    }
    
    # 4. Send the POST request to the server
    try:
        print(f"Sending POST request to {SERVER_URL}...")
        # The image bytes are sent as the main body (data) of the request
        response = requests.post(SERVER_URL, headers=headers, data=image_bytes, timeout=20)
        
        # 5. Print the server's response
        print("\n--- Server Response ---")
        print(f"Status Code: {response.status_code}")
        
        # Safely print the response body
        # Your new server correctly sends JSON for both success and errors
        try:
            print(f"Response Body: {response.json()}")
        except json.JSONDecodeError:
            # This is a fallback in case the server sends a non-JSON error (e.g., HTML)
            print(f"Response Body (not JSON): {response.text}")
        
        # Check for the success status code from your server
        if response.status_code == 201:
            print("\n✅ Simulation successful! A new record was created.")
            print("   Refresh your web browser to see the updated dashboard.")
        else:
            print("\n❌ Simulation failed. Check the Flask server logs for more details.")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ CRITICAL ERROR: Could not connect to the server at {SERVER_URL}.")
        print(f"   Error: {e}")
        print("   Please make sure your 'app.py' server is running and accessible.")

if __name__ == "__main__":
    run_simulation()