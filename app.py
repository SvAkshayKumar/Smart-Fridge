import os
import json
import re
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
    Only add the items that are low and my model is trained only on this list of items: Tomato, Apple, Eggs, Onion, Yogurt.
    In the recipe suggestions, only suggest recipes that can be made with the items in the fridge and only say the dish name.
    Use this structure EXACTLY:
    {{
      "isOrderRequired": <boolean>,
      "recipeSuggestions": ["<string>", "<string>", ...],
      "orderList": [{{"Productname": "Quantity"}}, {{"Productname": "Quantity"}}, ...]
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
            
            # Prepare payload
            notification_payload = {
                "orderList": order_list
            }

            # Build the record to insert
            notification_data = {
                "type": "order_suggestion",
                "title": notification_title,
                "message": "Click to view the shopping list prepared by Gemini.",
                "payload": notification_payload
            }

            # Insert into Supabase (assuming you've already initialized `supabase`)
            response = supabase.table("notifications").insert(notification_data).execute()

            # Optional: check the response
            if response.data:
                print("✅ Notification inserted successfully:", response.data)
            else:
                print("⚠️ Insert failed:", response.error)


        # Upload image to Supabase Storage
        file_name = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        supabase.storage.from_(IMAGE_BUCKET).upload(
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
                        # print(f"Parsed gemini_analysis: {record['gemini_analysis']}")
                        # print("recipeSuggestions:", record['gemini_analysis'].get('recipeSuggestions', []))
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

def parse_recipe_steps(text_response: str) -> list[str]:
    """
    Cleans and parses the raw text from Gemini into a list of recipe steps.
    This function is robust enough to handle numbered lists, bullet points, etc.
    """
    if not text_response:
        return []

    # Split the response by newlines to get individual lines
    lines = text_response.strip().split('\n')
    
    cleaned_steps = []
    for line in lines:
        # Remove any leading/trailing whitespace from the line
        clean_line = line.strip()
        
        # Use a regular expression to remove common list markers (e.g., "1.", "1)", "-", "*")
        clean_line = re.sub(r'^\s*\d+[\.\)]\s*|^\s*[\*\-]\s*', '', clean_line)
        
        # Only add the step if the line is not empty after cleaning
        if clean_line:
            cleaned_steps.append(clean_line)
            
    return cleaned_steps

# --- NEW API ENDPOINT FOR RECIPE STEPS ---
@app.route('/get_recipe_steps', methods=['POST'])
def get_recipe_steps():
    """
    Receives a recipe name, generates the steps using Gemini,
    and returns them in a JSON array.
    """
    # 1. Get the recipe name from the incoming request
    data = request.get_json()
    print("-"*20)
    print("-"*20)

    print("-"*20)

    print(data)
    print("-"*20)

    print("-"*20)
    print("-"*20)

    if not data or 'recipe_name' not in data:
        return jsonify({"error": "Missing 'recipe_name' in request body"}), 400

    recipe_name = data.get('recipe_name')
    print(f"Received request to generate steps for: {recipe_name}")

    # 2. Engineer a specific prompt for Gemini
    # This prompt instructs the model to only return the steps, making the output predictable.
    prompt = f"""
    You are a recipe assistant. Your task is to generate a concise, step-by-step recipe for "{recipe_name}".

    Follow these instructions EXACTLY:
    1.  Provide ONLY the cooking or preparation steps.
    2.  Do NOT include a title, an introduction, a list of ingredients, or any concluding remarks.
    3.  Format your entire response as a simple numbered or bulleted list.
    """

    try:
        # 3. Initialize the Gemini model and call the API
        # Using a model well-suited for instruction-following and generation.
        model = genai.GenerativeModel('gemini-2.5-flash') 
        response = model.generate_content(prompt)
        
        # 4. Parse the raw text response into a clean list of steps
        steps = parse_recipe_steps(response.text)
        
        if not steps:
            # Handle cases where Gemini might return an empty or unusable response
            print(f"Warning: Gemini did not return valid steps for '{recipe_name}'.")
            return jsonify({"error": f"Could not generate steps for '{recipe_name}'."}), 404

        print(f"✅ Successfully generated {len(steps)} steps for '{recipe_name}'.")
        # 5. Return the steps in the format expected by the frontend
        return jsonify({"steps": steps})

    except Exception as e:
        # Handle potential API errors (e.g., content safety blocks, network issues)
        print(f"CRITICAL ERROR calling Gemini for recipe steps: {e}")
        return jsonify({"error": "Failed to generate recipe steps due to an internal error."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)