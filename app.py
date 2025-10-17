import os
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
from datetime import datetime

# --- Configuration ---
# Get these from your Supabase project's API settings
SUPABASE_URL = "https://isgrdfhvghdhmbtauect.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlzZ3JkZmh2Z2hkaG1idGF1ZWN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1ODQ3NzEsImV4cCI6MjA3NjE2MDc3MX0.TKIjtSDz1_DoI987Rvkn2ZRWUYvX5wuuusL7cSet7lY"

# Initialize Flask App and Supabase Client
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

IMAGE_BUCKET = "images"

# --- Web Routes ---

@app.route('/')
def index():
    """Renders the main page, fetching and displaying all captured images."""
    try:
        response = supabase.table('captures').select("*").order('inserted_at', desc=True).execute()
        captures_data = response.data
        return render_template('index.html', captures=captures_data)
    except Exception as e:
        print(f"Error fetching data for index page: {e}")
        return "<h1>Error loading data. See server logs.</h1>", 500


@app.route('/newdata', methods=['POST'])
def new_data():
    """Endpoint to receive data from the ESP32-CAM."""
    # This function remains exactly the same as before.
    print("Received new data request...")
    if 'imageFile' not in request.files:
        return jsonify({"status": "error", "message": "No image file part"}), 400
    image_file = request.files['imageFile']
    metadata_text = request.form.get('metadata', '{}')
    if image_file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    try:
        file_extension = os.path.splitext(image_file.filename)[1]
        unique_filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        image_bytes = image_file.read()
        
        supabase.storage.from_(IMAGE_BUCKET).upload(
            file=image_bytes, path=unique_filename, file_options={"content-type": image_file.mimetype}
        )
        public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(unique_filename)
        
        db_insert_response = supabase.table('captures').insert({
            'image_url': public_url, 'metadata': metadata_text 
        }).execute()
        
        if len(db_insert_response.data) > 0:
            print("Successfully saved data.")
            return jsonify({"status": "success", "message": "Image uploaded successfully"}), 201
        else:
            raise Exception("Failed to insert data into the database.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# <<< NEW >>> Endpoint for dynamic updates
@app.route('/latest')
def latest_capture():
    """
    Returns the most recent capture data as JSON.
    The frontend will poll this to check for new images.
    """
    try:
        # Fetch only the single most recent record
        response = supabase.table('captures').select("*").order('inserted_at', desc=True).limit(1).single().execute()
        return jsonify(response.data)
    except Exception as e:
        # It's okay if this fails (e.g., no data yet), return an empty object
        print(f"Error fetching latest data: {e}")
        return jsonify({})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)