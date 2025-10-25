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
    itemList_Cart = [
        { 'id': 'onion','description': '1 Pack / 900-1000 gm'},
        { 'id': 'tomato','description': '1 kg'},
        { 'id': 'apple','description': '4 pieces'},
        { 'id': 'eggs','description': 'Pack of 6'},
        { 'id': 'yogurt','description': '400 gm Cup'}, 
    ]
    prompt = f"""
    You are a smart fridge assistant. Your response MUST be a single, valid JSON object starting with {{ and ending with }}.
    Do NOT include any markdown formatting like ```json.
    this is the list of items currently in the fridge: {json.dumps(items_list)}.
    Based on these items, determine if a grocery order is needed. If so, suggest recipes and create a shopping list.
    Respond ONLY in JSON format following this schema:
    Only add the items that are low and my model is trained only on this list of items: Tomato, Apple, Eggs, Onion, Yogurt.
    In the recipe suggestions, only suggest recipes that can be made with the items in the fridge and only say the dish name.
    Use this structure EXACTLY:
    Remember that the item is read as the individual item but the ordering application has this kind of structure and wisely and
    remember that for some items quantity 1 means 5 peice and for some quantity 1 means 1 kg etc so be wise while suggesting the order list.
    this is the list from my application {itemList_Cart} i need you to put the number itself not the description in the order list quantity.
    Note : Assume that you are planner for 3 people home and It is not necessary to order all items, only those that are low based on typical fridge usage.
    Example like this:
    {{
      "isOrderRequired": <boolean>,
      "recipeSuggestions": ["<string>", "<string>", ...],
      "orderList": [{{"tomato": "1"}}, {{"eggs": "2"}}, ...]
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
@app.route('/alert', methods=['POST'])
def get_alert():
    try:

        # --- REVISED NOTIFICATION TEXT ---
        notification_data = {
            "type": "door_alert",
            "title": "Fridge Door Alert",
            "message": "The refrigerator door appears to have been left open for more then 10 Minutes. Please close it to ensure food safety and energy efficiency.",
            "payload": { "alert_type": "door_open" } # Using a structured payload is better practice
        }

        # Insert into Supabase
        response = supabase.table("notifications").insert(notification_data).execute()

        # Check the response
        if response.data:
            print("✅ Door alert notification inserted successfully:", response.data)
            return jsonify({"status": "success", "message": "Alert processed successfully"}), 201
        else:
            print("⚠️ Notification insert failed:", response.error)
            # It's better to return a server error if the database operation fails
            return jsonify({"status": "error", "message": "Failed to store notification"}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    
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
            
            if num_items > 0:
                # --- Create a dynamic message with a preview ---
                
                # 1. Generate the preview string (e.g., "2 x Tomato, 1 x Onion")
                preview_items = []
                # Take the first two items for the preview
                for item_dict in order_list[:2]: 
                    product_name = list(item_dict.keys())[0]
                    quantity = item_dict[product_name]
                    preview_items.append(f"{quantity} x {product_name}")
                preview_text = ", ".join(preview_items)

                # 2. Create fun, dynamic titles and messages
                title = f"Don't Get Hangry! Your Cart is Ready."
                
                if num_items > 2:
                    # If there are more items than the preview shows
                    message = f"You're running low on essentials<br>{preview_text}, and more.<br>Tap to restock now!"
                else:
                    # If the preview shows all the items
                    message = f"You're running low on<br>{preview_text}.<br>Tap to restock now!"

                # 3. Build the final notification record
                notification_payload = {"orderList": order_list}
                notification_data = {
                    "type": "order_suggestion",
                    "title": title,
                    "message": f"{message}<br>You have <b>{num_items} items</b> in your cart.",
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

# --- (Keep your existing parse_recipe_steps helper function as is) ---
def parse_recipe_steps(text_response: str) -> list[str]:
    """
    Cleans and parses the raw text from Gemini into a list of recipe steps.
    """
    if not text_response:
        return []
    lines = text_response.strip().split('\n')
    cleaned_steps = []
    for line in lines:
        clean_line = line.strip()
        clean_line = re.sub(r'^\s*\d+[\.\)]\s*|^\s*[\*\-]\s*', '', clean_line)
        if clean_line:
            cleaned_steps.append(clean_line)
    return cleaned_steps

# --- MODIFIED API ENDPOINT FOR RECIPE STEPS ---
@app.route('/get_recipe_steps', methods=['POST'])
def get_recipe_steps():
    """
    Receives a recipe name and a list of available items, generates steps 
    using Gemini, and returns them in a JSON array.
    """
    data = request.get_json()
    if not data or 'recipe_name' not in data:
        return jsonify({"error": "Missing 'recipe_name' in request body"}), 400

    recipe_name = data.get('recipe_name')
    # MODIFIED: Get the list of available items from the request. Default to an empty list.
    available_items = data.get('available_items', [])
    
    print(f"Generating steps for '{recipe_name}' with items: {available_items}")

    # MODIFIED: Create a simple string representation of the inventory for the prompt.
    # This converts the list of objects into a human-readable string.
    if available_items:
        items_string = ", ".join([f"{item.get('quantity', 1)} x {item.get('type', '')}" for item in available_items])
    else:
        items_string = "what is available" # Fallback text if the list is empty

    # MODIFIED: The prompt now includes the available ingredients, making it much more powerful.
    prompt = f"""
    You are a recipe assistant. Your task is to generate a concise, step-by-step recipe for "{recipe_name}" using ONLY the ingredients available in the fridge.

    Available Ingredients: {items_string}.
    Assume that my model is only trained on this list of items: Tomato, Apple, Eggs, Onion, Yogurt.

    Follow these instructions EXACTLY:
    1.  Base the entire recipe on the "Available Ingredients".
    2.  If a common pantry staple (like oil, salt, pepper, water, flour) is absolutely necessary but not listed, you may assume it is available.
    3.  Do NOT suggest ingredients that are not on the available list.
    4.  Provide ONLY the cooking or preparation steps.
    5.  Do NOT include a title, an introduction, a list of ingredients, or any concluding remarks.
    6.  Format your entire response as a simple numbered or bulleted list.
    7.  Each step should be clear and concise.
    8.  Your response MUST be a plain text list of steps, without any markdown formatting.
    9.  In the end add this line "Enjoy your (Name of the recipe as mentioned!)" as the last step.
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        steps = parse_recipe_steps(response.text)
        
        if not steps:
            print(f"Warning: Gemini did not return valid steps for '{recipe_name}'.")
            return jsonify({"error": f"Could not generate steps for '{recipe_name}'."}), 404

        print(f"✅ Successfully generated {len(steps)} steps for '{recipe_name}'.")
        return jsonify({"steps": steps})

    except Exception as e:
        print(f"CRITICAL ERROR calling Gemini for recipe steps: {e}")
        return jsonify({"error": "Failed to generate recipe steps due to an internal error."}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)