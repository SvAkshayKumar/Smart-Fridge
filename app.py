
from flask import Flask, render_template, Response
import requests

app = Flask(__name__)

# --- IMPORTANT ---
# Replace this with the IP address from your ESP32's Serial Monitor
ESP32_CAM_IP = "192.168.0.107" # CHANGE THIS!
ESP32_CAM_URL = f"http://{ESP32_CAM_IP}/capture"

@app.route('/')
def index():
    """Serves the main HTML page with the button."""
    return render_template('index.html')

@app.route('/get_image')
def get_image():
    """
    Fetches the JPEG image from the ESP32 and relays it to the browser.
    """
    try:
        # Request the JPEG image from the ESP32-CAM
        response = requests.get(ESP32_CAM_URL, timeout=10)
        
        # Raise an exception if the request was not successful
        response.raise_for_status()
        
        # Return the response directly to the browser.
        # The content (the JPEG image) and headers are passed through.
        return Response(response.content, mimetype='image/jpeg')

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to ESP32-CAM: {e}")
        return "Error: Could not connect to ESP32-CAM.", 500

if __name__ == '__main__':
    # Make the server accessible on your local network
    app.run(host='0.0.0.0', port=5000)
