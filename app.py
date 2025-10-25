import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from supabase import create_client, Client
from datetime import datetime, timedelta
import google.generativeai as genai

# --- Configuration ---
SUPABASE_URL = "https://isgrdfhvghdhmbtauect.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlzZ3JkZmh2Z2hkaG1idGF1ZWN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1ODQ3NzEsImV4cCI6MjA3NjE2MDc3MX0.TKIjtSDz1_DoI987Rvkn2ZRWUYvX5wuuusL7cSet7lY"
GEMINI_API_KEY = "AIzaSyCgoPSqsQge_7nZO0L5alYy3Gb7qRja9EA"

# --- Initialize Clients ---
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
IMAGE_BUCKET = "images"
genai.configure(api_key=GEMINI_API_KEY)

# --- Gemini Function (Unchanged) ---
def get_gemini_suggestions(items_list):
    # This function is unchanged as its core logic is sound.
    model = genai.GenerativeModel('gemini-2.5-flash') # Using a recommended model
    prompt = f"""
    You are a smart fridge assistant. Your response MUST be a single, valid JSON object starting with {{ and ending with }}.
    Do NOT include any markdown formatting like ```json.
    this is the list of items currently in the fridge: {json.dumps(items_list)}.
    Based on these items, determine if a grocery order is needed. If so, suggest recipes and create a shopping list.
    Respond ONLY in JSON format following this schema:
    Use this structure EXACTLY:
    {{
      "isOrderRequired": <boolean>,
      "recipeSuggestions": ["<string>", "<string>", ...],
      "orderList": ["<string>", "<string>", ...]
    }}
    """
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text) if cleaned_text else None
    except Exception as e:
        print(f"CRITICAL ERROR calling Gemini: {e}")
        return None

# --- Web Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/order-placed')
def order_placed():
    return render_template('order_placed.html')

# Serve static files like CSS and JS
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# --- API Endpoints ---
@app.route('/newdata', methods=['POST'])
def new_data():
    # This route's core data receiving logic is unchanged as requested.
    try:
        metadata_text = request.headers.get('X-Metadata')
        image_bytes = request.get_data()
        items_list = json.loads(metadata_text).get("items", [])
        
        gemini_analysis = get_gemini_suggestions(items_list)
        if gemini_analysis is None:
            return jsonify({"status": "error", "message": "AI analysis failed"}), 500

        # --- MODIFIED: Dynamic Notification Title ---
        if gemini_analysis.get("isOrderRequired"):
            order_list = gemini_analysis.get("orderList", [])
            num_items = len(order_list)
            # Create a more informative notification title
            notification_title = f"New suggestion from agent: {num_items} items in cart"
            
            notification_payload = {"orderList": order_list}
            supabase.table("notifications").insert({
                "type": "order_suggestion",
                "title": notification_title,
                "message": "Click to view the shopping list prepared by Gemini.",
                "payload": notification_payload
            }).execute()

        # Upload image to Supabase Storage
        file_name = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        upload_response = supabase.storage.from_(IMAGE_BUCKET).upload(
            path=file_name,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )

        public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(file_name)

        # Insert record into 'captures' table
        supabase.table('captures').insert({
            'image_url': public_url,
            'items': items_list,
            'gemini_analysis': json.dumps(gemini_analysis)
        }).execute()

        return jsonify({"status": "success", "message": "Upload successful"}), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# --- NEW: Endpoint to get the last 5 records ---
@app.route('/latest-records')
def latest_records():
    try:
        response = supabase.table('captures').select("*").order('inserted_at', desc=True).limit(5).execute()
        
        if response.data:
            # Process each record to parse the gemini_analysis JSON string
            for record in response.data:
                if 'gemini_analysis' in record and isinstance(record['gemini_analysis'], str):
                    try:
                        record['gemini_analysis'] = json.loads(record['gemini_analysis'])
                    except json.JSONDecodeError:
                        record['gemini_analysis'] = {} # Handle malformed JSON
            return jsonify(response.data)
        return jsonify([]) # Return an empty list if no records found
    except Exception as e:
        print(f"Error fetching latest records: {e}")
        return jsonify([])

# --- Notification Endpoints (Unchanged) ---
@app.route('/notifications', methods=['GET'])
def get_notifications():
    try:
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        response = supabase.table('notifications').select('*').eq('is_read', False).gte('inserted_at', twenty_four_hours_ago).order('inserted_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/notifications/mark-as-read', methods=['POST'])
def mark_as_read():
    try:
        data = request.get_json()
        notification_id = data.get('id')
        if not notification_id:
            return jsonify({"error": "Notification ID is required"}), 400
        
        supabase.table('notifications').update({'is_read': True}).eq('id', notification_id).execute()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)