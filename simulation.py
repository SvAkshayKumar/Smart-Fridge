# Import necessary libraries
import requests # This line is crucial for making HTTP requests
import json
import random
import time

# --- Configuration ---
# Ensure this IP address is correct for the machine running your Flask server

NEW_DATA_URL = f"https://iot-smart-fridge.onrender.com/newdata" 
ALERT_URL = f"https://iot-smart-fridge.onrender.com/alert" # New URL for the alert endpoint

# --- ACTION REQUIRED: EDIT THIS LINE ---
# Change this to the exact filename of the image in the same folder.
IMAGE_FILE_PATH = "testing_combined.jpg"
# --------------------------------------

# --- Helper Functions (Unchanged) ---

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
    possible_items = ["Tomato", "Apple", "Eggs", "Onion", "Yogurt"]
    num_items = random.randint(0, 4)
    selected_items = random.sample(possible_items, num_items)
    inventory_list = []
    for item_name in selected_items:
        quantity = random.randint(1, 2)
        inventory_list.append({"type": item_name, "quantity": quantity})
    
    metadata_object = {"items": inventory_list}
    return json.dumps(metadata_object)

# --- Main Simulation Logic (Unchanged) ---

def run_data_simulation():
    """
    Main function to prepare and send the simulated data to your Flask server.
    """
    print("\n--- Simulating New Data Upload (Fridge Scan) ---")
    
    # 1. Load the image from the specified file
    image_bytes = load_image_from_file(IMAGE_FILE_PATH)
    if image_bytes is None:
        print("Aborting simulation due to image loading error.")
        return

    # 2. Generate the sample inventory JSON string
    inventory_json_string = generate_sample_inventory()
    print(f"Generated Inventory: {inventory_json_string}")
    
    # 3. Prepare the HTTP request headers.
    headers = {
        'X-Metadata': inventory_json_string,
        'Content-Type': 'image/jpeg'
    }
    
    # 4. Send the POST request to the server
    try:
        print(f"Sending POST request to {NEW_DATA_URL}...")
        response = requests.post(NEW_DATA_URL, headers=headers, data=image_bytes, timeout=20)
        
        # 5. Print the server's response
        print("\n--- Server Response ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            print(f"Response Body: {response.json()}")
        except json.JSONDecodeError:
            print(f"Response Body (not JSON): {response.text}")
        
        if response.status_code == 201:
            print("\n✅ Simulation successful! A new record was created.")
        else:
            print("\n❌ Simulation failed. Check the Flask server logs for details.")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ CRITICAL ERROR: Could not connect to the server at {NEW_DATA_URL}.")
        print(f"   Error: {e}\n   Please ensure your 'app.py' server is running and accessible.")

# --- NEW: Door Alert Simulation Logic ---

def simulate_door_alert():
    """
    Sends a request to the /alert endpoint to test the door open notification.
    """
    print("\n--- Simulating Fridge Door Open Alert ---")

    # The /alert route expects a metadata header, even if it doesn't use the items.
    # We send a dummy payload to match the server's expectation.
    dummy_metadata = json.dumps({"items": []})
    
    headers = {
        'X-Metadata': dummy_metadata,
        # 'Content-Type' is not needed as we are not sending a body
    }

    try:
        print(f"Sending POST request to {ALERT_URL}...")
        # No 'data' parameter is needed as this is just a trigger.
        response = requests.post(ALERT_URL, headers=headers, timeout=10)

        print("\n--- Server Response ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            print(f"Response Body: {response.json()}")
        except json.JSONDecodeError:
            print(f"Response Body (not JSON): {response.text}")
        
        if response.status_code == 201:
            print("\n✅ Alert simulation successful! A new notification was created.")
        else:
            print("\n❌ Simulation failed. Check the Flask server logs for details.")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ CRITICAL ERROR: Could not connect to the server at {ALERT_URL}.")
        print(f"   Error: {e}\n   Please ensure your 'app.py' server is running and accessible.")


# --- MODIFIED: Main Execution Block with User Choice ---

if __name__ == "__main__":
    while True:
        print("\n--- ESP32 Simulation Menu ---")
        print("1. Simulate New Fridge Data (Image + Inventory)")
        print("2. Simulate Fridge Door Open Alert")
        print("3. Exit")
        
        choice = input("Enter your choice (1, 2, or 3): ")
        
        if choice == '1':
            run_data_simulation()
        elif choice == '2':
            simulate_door_alert()
        elif choice == '3':
            print("Exiting simulation.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
        
        time.sleep(2) # A small delay before showing the menu again