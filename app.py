import os
import json
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from supabase import create_client, Client
from datetime import datetime, timedelta
import google.generativeai as genai
import traceback

# --- Import the prediction function from your model.py file ---
from model import predict_and_count_items

# --- Configuration ---
SUPABASE_URL = "https://isgrdfhvghdhmbtauect.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlzZ3JkZmh2Z2hkaG1idGF1ZWN0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA1ODQ3NzEsImV4cCI6MjA3NjE2MDc3MX0.TKIjtSDz1_DoI987Rvkn2ZRWUYvX5wuuusL7cSet7lY"
GEMINI_API_KEY = "AIzaSyCgoPSqsQge_7nZO0L5alYy3Gb7qRja9EA"

# --- Initialize Clients ---
app = Flask(__name__)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
IMAGE_BUCKET = "images"
genai.configure(api_key=GEMINI_API_KEY)


# --- Gemini Function (CORRECTED MODEL NAME) ---
def get_gemini_suggestions(items_list):
    # --- START OF FIX ---
    # Changed model name to the stable and universally available 'gemini-pro'.
    model_gen = genai.GenerativeModel('gemini-2.5-flash')
    # --- END OF FIX ---
    
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
    Note : It is not necessary to order all items, only add those which is really needed do the billing as minimum as possible based on typical fridge usage.
           and also order the items in such a way that it should be sufficient for only today for 3 people home.
    Example like this:
    {{
      "isOrderRequired": <boolean>,
      "recipeSuggestions": ["<string>", "<string>", ...],
      "orderList": [{{"tomato": "1"}}, {{"eggs": "2"}}, ...]
    }}
    """
    try:
        response = model_gen.generate_content(prompt)
        cleaned_text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned_text) if cleaned_text else None
    except Exception as e:
        print(f"CRITICAL ERROR calling Gemini: {e}")
        return None

# --- Web Routes (Unchanged) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/order-placed')
def order_placed():
    return render_template('order_placed.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# --- API Endpoints ---
@app.route('/alert', methods=['POST'])
def get_alert():
    try:
        notification_data = {
            "type": "door_alert", "title": "Fridge Door Alert",
            "message": "The refrigerator door appears to have been left open for more then 10 Minutes. Please close it to ensure food safety and energy efficiency.",
            "payload": { "alert_type": "door_open" }
        }
        response = supabase.table("notifications").insert(notification_data).execute()
        if response.data:
            print("✅ Door alert notification inserted successfully.")
            return jsonify({"status": "success", "message": "Alert processed successfully"}), 201
        else:
            print(f"⚠️ Notification insert failed: {response.error}")
            return jsonify({"status": "error", "message": "Failed to store notification"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route('/newdata', methods=['POST'])
def new_data():
    try:
        image_bytes = request.get_data()
        if not image_bytes:
            return jsonify({"status": "error", "message": "No image data received"}), 400

        print("📸 Image received. Calling model for object detection...")
        items_list = predict_and_count_items(image_bytes)
        
        gemini_analysis = get_gemini_suggestions(items_list)
        print(gemini_analysis)
        print(items_list)
        if gemini_analysis is None:
            return jsonify({"status": "error", "message": "AI analysis failed"}), 500

        if gemini_analysis.get("isOrderRequired"):
            order_list = gemini_analysis.get("orderList", [])
            print(order_list)
            num_items = len(order_list)
            print(num_items)
            
            if num_items > 0:
                preview_items = []
                for item_dict in order_list[:2]:
                    print(item_dict)
                    product_name_str = list(item_dict.keys())[0]
                    quantity = item_dict[product_name_str]
                    # Use the string (not a list) for the preview text
                    preview_items.append(f"{quantity} x {product_name_str.capitalize()}")
                    # --- END OF FIX ---
                preview_text = ", ".join(preview_items)

                title = "Don't Get Hangry! Your Cart is Ready."
                if num_items > 2:
                    message = f"You're running low on essentials like {preview_text}, and more.<br>Tap to restock now!"
                else:
                    message = f"You're running low on {preview_text}.<br>Tap to restock now!"
                
                notification_data = {
                    "type": "order_suggestion", "title": title, "message": message,
                    "payload": {"orderList": order_list}
                }
                print(order_list)
                supabase.table("notifications").insert(notification_data).execute()

        file_name = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        supabase.storage.from_(IMAGE_BUCKET).upload(
            path=file_name, file=image_bytes, file_options={"content-type": "image/jpeg"}
        )
        public_url = supabase.storage.from_(IMAGE_BUCKET).get_public_url(file_name)

        supabase.table('captures').insert({
            'image_url': public_url,
            'items': items_list,
            'gemini_analysis': json.dumps(gemini_analysis)
        }).execute()

        return jsonify({"status": "success", "message": "Upload and analysis successful"}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Other Endpoints (Unchanged) ---
@app.route('/latest-records')
def latest_records():
    try:
        response = supabase.table('captures').select("*").order('inserted_at', desc=True).limit(5).execute()
        if response.data:
            for record in response.data:
                if 'gemini_analysis' in record and isinstance(record['gemini_analysis'], str):
                    try: record['gemini_analysis'] = json.loads(record['gemini_analysis'])
                    except json.JSONDecodeError: record['gemini_analysis'] = {}
            return jsonify(response.data)
        return jsonify([])
    except Exception as e: return jsonify([])

@app.route('/notifications', methods=['GET'])
def get_notifications():
    try:
        twenty_four_hours_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        response = supabase.table('notifications').select('*').eq('is_read', False).gte('inserted_at', twenty_four_hours_ago).order('inserted_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/notifications/mark-as-read', methods=['POST'])
def mark_as_read():
    try:
        data = request.get_json()
        notification_id = data.get('id')
        if not notification_id: return jsonify({"error": "Notification ID is required"}), 400
        supabase.table('notifications').update({'is_read': True}).eq('id', notification_id).execute()
        return jsonify({"status": "success"})
    except Exception as e: return jsonify({"error": str(e)}), 500

def parse_recipe_steps(text_response: str) -> list[str]:
    if not text_response: return []
    lines = text_response.strip().split('\n')
    cleaned_steps = []
    for line in lines:
        clean_line = line.strip()
        clean_line = re.sub(r'^\s*\d+[\.\)]\s*|^\s*[\*\-]\s*', '', clean_line)
        if clean_line: cleaned_steps.append(clean_line)
    return cleaned_steps

@app.route('/get_recipe_steps', methods=['POST'])
def get_recipe_steps():
    data = request.get_json()
    if not data or 'recipe_name' not in data:
        return jsonify({"error": "Missing 'recipe_name' in request body"}), 400
    recipe_name = data.get('recipe_name')
    available_items = data.get('available_items', [])
    if available_items:
        items_string = ", ".join([f"{item.get('quantity', 1)} x {item.get('type', '')}" for item in available_items])
    else: items_string = "what is available"
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
    9.  In the end add this line "Enjoy your {recipe_name}!" as the last step.
    """
    try:
        model_gen = genai.GenerativeModel('gemini-2.5-flash') # Using the corrected model name here too
        response = model_gen.generate_content(prompt)
        steps = parse_recipe_steps(response.text)
        if not steps: return jsonify({"error": f"Could not generate steps for '{recipe_name}'."}), 404
        return jsonify({"steps": steps})
    except Exception as e: return jsonify({"error": "Failed to generate recipe steps due to an internal error."}), 500