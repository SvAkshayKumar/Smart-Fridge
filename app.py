import os
import json
from flask import Flask, request, jsonify, render_template
from supabase import create_client, Client
from datetime import datetime
import google.generativeai as genai

# --- Configuration (Using your provided credentials) ---
SUPABASE_URL = "https://isgrdfhvghdhmbtauect.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlzZ3JkZmh2Z2hkaG1idGF1ZWN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1ODQ3NzEsImV4cCI6MjA3NjE2MDc3MX0.TKIjtSDz1_DoI987Rvkn2ZRWUYvX5wuuusL7cSet7lY"
GEMINI_API_KEY = "AIzaSyCgoPSqsQge_7nZO0L5alYy3Gb7qRja9EA"

# --- Initialize Clients ---
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
IMAGE_BUCKET = "images"

genai.configure(api_key=GEMINI_API_KEY)

# --- Gemini LLM Integration (This part is now correct) ---
def get_gemini_suggestions(items_list):
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    You are a smart fridge assistant. Your response MUST be a single, valid JSON object starting with {{ and ending with }}.
    Do NOT include any markdown formatting like ```json.
    Current Inventory: {json.dumps(items_list)}
    Use this structure EXACTLY:
    {{
      "isOrderRequired": <boolean>, "recipeSuggestions": ["<string>", ...], "orderList": [ ... ], "suggestedAddons": [ ... ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        if not cleaned_text:
            return None
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"CRITICAL ERROR calling Gemini or parsing JSON: {e}")
        return None

# --- Web Routes ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/cart')
def cart(): return render_template('cart.html')
    
@app.route('/order-placed')
def order_placed(): return render_template('order_placed.html')

# --- API Endpoints ---
@app.route('/newdata', methods=['POST'])
def new_data():
    print("Received new data request...")
    metadata_text = request.headers.get('X-Metadata')
    image_bytes = request.get_data()

    if not image_bytes or not metadata_text:
        return jsonify({"status": "error", "message": "Missing image or metadata"}), 400
    
    try:
        items_list = json.loads(metadata_text).get("items", [])
        gemini_analysis_object = get_gemini_suggestions(items_list)
        
        if gemini_analysis_object is None:
            print("Aborting request because Gemini analysis failed.")
            return jsonify({"status": "error", "message": "Failed to get analysis from AI model"}), 500
        
        unique_filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        supabase.storage.from_(IMAGE_BUCKET).upload(file=image_bytes, path=unique_filename, file_options={"content-type": "image/jpeg"})
        public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(unique_filename)
        
        db_insert_data = {
            'image_url': public_url, 
            'items': items_list,
            # --- THE FINAL FIX ---
            # We must convert the Python dictionary to a valid JSON STRING before inserting.
            # This ensures it's stored correctly and can be parsed by JavaScript.
            'gemini_analysis': json.dumps(gemini_analysis_object)
            # --- END OF FIX ---
        }
        supabase.table('captures').insert(db_insert_data).execute()
        print("Successfully processed and SAVED AS VALID JSON.")

        return jsonify({"status": "success", "message": "Upload successful"}), 201
    except Exception as e:
        print(f"An internal error occurred in /newdata: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/latest')
def latest_capture():
    # This function is correct and needs no changes. It will now receive correct data.
    try:
        response = supabase.table('captures').select("*").order('inserted_at', desc=True).limit(1).single().execute()
        if response.data:
            return jsonify(response.data)
        return jsonify({"image_url": None, "items": [], "gemini_analysis": "{}"})
    except Exception as e:
        print(f"Error fetching latest data: {e}")
        return jsonify({})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)