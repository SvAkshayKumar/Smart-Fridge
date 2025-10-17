from flask import Flask, render_template, Response
import requests

app = Flask(__name__)

# --- IMPORTANT ---
# Replace this with the IP address of your ESP32-CAM from the Arduino Serial Monitor
ESP32_IP = "192.168.0.105" # CHANGE THIS!
ESP32_STREAM_URL = f"http://{ESP32_IP}/stream"

def generate_video_stream():
    """
    Connects to the ESP32 stream and forwards the data chunk by chunk.
    """
    try:
        # The 'stream=True' is crucial for this to work
        with requests.get(ESP32_STREAM_URL, stream=True, timeout=10) as r:
            if r.status_code == 200:
                # Yield each chunk of the response (which is part of the MJPEG stream)
                for chunk in r.iter_content(chunk_size=1024):
                    yield chunk
            else:
                print(f"Error receiving stream from ESP32: {r.status_code}")
                yield b'' # Yield empty bytes if error
    except requests.exceptions.RequestException as e:
        print(f"Could not connect to ESP32 stream: {e}")
        yield b'' # Yield empty bytes if connection fails

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """
    This is the endpoint the browser will connect to.
    It returns the streaming response from the ESP32.
    """
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=--frame')

if __name__ == '__main__':

    app.run(debug=True,host='0.0.0.0', port=5000)
