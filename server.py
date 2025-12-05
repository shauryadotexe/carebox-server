from flask import Flask, request, jsonify
import csv
import os
import uuid
import json  # <--- Added json import

# --- GLOBAL VARIABLES ---
ACTIVE_CALL = None
DATA_FILE = 'patient_data.csv'
CREDENTIALS_FILE = 'doctors_access_list.json' # <--- The file we just made

app = Flask(__name__)

CHAT_HISTORY = {}

# ... (existing routes) ...

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = data.get('room_id') # Use patient_name or a unique call ID
    sender = data.get('sender')
    message = data.get('message')
    
    if not room_id or not sender or not message:
        return jsonify({"error": "Missing data"}), 400
        
    if room_id not in CHAT_HISTORY:
        CHAT_HISTORY[room_id] = []
        
    CHAT_HISTORY[room_id].append({'sender': sender, 'text': message})
    return jsonify({"status": "success"})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    room_id = request.args.get('room_id')
    
    if not room_id:
        return jsonify({"error": "Missing room_id"}), 400
        
    # Return list of messages, default to empty list if none exist
    messages = CHAT_HISTORY.get(room_id, [])
    return jsonify({"messages": messages})

# --- 1. DOCTOR LOGIN ENDPOINT (NEW) ---
@app.route('/doctor_login', methods=['POST'])
def doctor_login():
    """
    Reads the secure JSON file and verifies credentials.
    """
    # 1. Get data from the App
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # 2. Check if the "Database" file exists
    if not os.path.exists(CREDENTIALS_FILE):
        return jsonify({"success": False, "message": "Server Error: Credentials file missing"}), 500

    try:
        # 3. Open the file and check the name/password
        with open(CREDENTIALS_FILE, 'r') as f:
            valid_users = json.load(f)
            
        if username in valid_users and valid_users[username] == password:
            print(f"LOGIN SUCCESS: {username}")
            return jsonify({"success": True, "message": "Access Granted"})
        else:
            print(f"LOGIN FAILED: {username}")
            return jsonify({"success": False, "message": "Invalid Credentials"}), 401
            
    except Exception as e:
        print(f"Login Error: {e}")
        return jsonify({"success": False, "message": "Internal Server Error"}), 500

# --- 2. CALL HANDLING ENDPOINTS (Existing) ---
@app.route('/start_call', methods=['GET'])
def start_call():
    global ACTIVE_CALL
    patient_name = request.args.get('patient_name')
    
    room_id = "CareBox-Call-" + str(uuid.uuid4())[:8]
    room_url = f"https://meet.jit.si/{room_id}"

    ACTIVE_CALL = {
        "url": room_url,
        "patient_name": patient_name
    }
    return jsonify({"url": room_url})

@app.route('/get_active_call', methods=['GET'])
def get_active_call():
    global ACTIVE_CALL
    if ACTIVE_CALL:
        data = ACTIVE_CALL
        ACTIVE_CALL = None 
        return jsonify(data)
    else:
        return jsonify(None)

# --- 3. DATA & NOTES ENDPOINTS (Existing) ---
@app.route('/submit_patient', methods=['POST'])
def handle_patient_submission():
    data = request.json
    file_exists = os.path.isfile(DATA_FILE)
    try:
        with open(DATA_FILE, mode='a', newline='') as file:
            fieldnames = ['name', 'age', 'sex']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(data)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"}), 500

@app.route('/get_patient', methods=['GET'])
def get_patient():
    name_to_find = request.args.get('name')
    if not name_to_find: return jsonify({"error": "No name provided"}), 400
    try:
        with open(DATA_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['name'].lower() == name_to_find.lower():
                    return jsonify(row)
        return jsonify({"error": "Not found"}), 404
    except:
        return jsonify({"error": "Server error"}), 500

@app.route('/get_notes', methods=['GET'])
def get_notes():
    patient_name = request.args.get('name')
    # Ensure notes folder exists
    if not os.path.exists("patient_notes"): os.makedirs("patient_notes")
    
    filepath = os.path.join("patient_notes", f"{patient_name}.txt")
    if os.path.exists(filepath):
        with open(filepath, 'r') as f: return jsonify({"notes": f.read()})
    return jsonify({"notes": ""})

@app.route('/update_notes', methods=['POST'])
def update_notes():
    data = request.json
    patient_name = data.get('name')
    notes = data.get('notes')
    
    if not os.path.exists("patient_notes"): os.makedirs("patient_notes")
    
    filepath = os.path.join("patient_notes", f"{patient_name}.txt")
    with open(filepath, 'w') as f: f.write(notes)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
