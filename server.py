from flask import Flask, request, jsonify, render_template_string
import csv
import os
import uuid
import json
from datetime import datetime

# --- GLOBAL VARIABLES ---
ACTIVE_CALL = None
DATA_FILE = 'patient_data.csv'
CREDENTIALS_FILE = 'doctors_access_list.json'

app = Flask(__name__)

CHAT_HISTORY = {}

# --- 1. DOCTOR LOGIN ---
@app.route('/doctor_login', methods=['POST'])
def doctor_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # Ensure credentials file exists
    if not os.path.exists(CREDENTIALS_FILE):
        # Create a default one if missing
        default_creds = {"admin": "admin"}
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(default_creds, f)
            
    try:
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

# --- 2. CALL HANDLING ---
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

# --- 3. PATIENT DATA & LOGGING ---
@app.route('/submit_patient', methods=['POST'])
def handle_patient_submission():
    data = request.json
    
    # Add Timestamp
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(DATA_FILE)
    try:
        with open(DATA_FILE, mode='a', newline='') as file:
            fieldnames = ['name', 'age', 'sex', 'timestamp']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            # Write header if file is new
            if not file_exists: 
                writer.writeheader()
            
            writer.writerow(data)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error saving patient: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/get_patient', methods=['GET'])
def get_patient():
    name_to_find = request.args.get('name')
    if not name_to_find: return jsonify({"error": "No name provided"}), 400
    
    if not os.path.exists(DATA_FILE):
        return jsonify({"error": "No database found"}), 404
        
    try:
        with open(DATA_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['name'].lower() == name_to_find.lower():
                    return jsonify(row)
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- NEW: VIEW ALL LOGS IN BROWSER ---
@app.route('/view_logs', methods=['GET'])
def view_logs():
    """
    Returns a simple HTML page to view the CSV data in the browser.
    Accessible via: https://your-server-url.com/view_logs
    """
    if not os.path.exists(DATA_FILE):
        return "<h3>No logs available yet.</h3>"

    rows = []
    try:
        with open(DATA_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            rows = list(reader)
    except Exception as e:
        return f"Error reading log: {e}"

    # Simple HTML Template
    html = """
    <html>
    <head>
        <title>CareBox Patient Logs</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f9; }
            table { border-collapse: collapse; width: 100%; box-shadow: 0 0 20px rgba(0,0,0,0.1); background: white; }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #009688; color: white; }
            tr:hover { background-color: #f1f1f1; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Patient Login History</h1>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Name</th>
                    <th>Age</th>
                    <th>Gender</th>
                </tr>
            </thead>
            <tbody>
                {% for row in rows %}
                <tr>
                    <td>{{ row.get('timestamp', 'N/A') }}</td>
                    <td>{{ row.get('name') }}</td>
                    <td>{{ row.get('age') }}</td>
                    <td>{{ row.get('sex') }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </body>
    </html>
    """
    return render_template_string(html, rows=rows)

# --- NEW: API TO GET ALL LOGS (JSON) ---
@app.route('/get_all_patients', methods=['GET'])
def get_all_patients():
    if not os.path.exists(DATA_FILE):
        return jsonify([])
    try:
        with open(DATA_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            return jsonify(list(reader))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- CHAT & NOTES (Existing) ---
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = data.get('room_id')
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
    messages = CHAT_HISTORY.get(room_id, [])
    return jsonify({"messages": messages})

@app.route('/get_notes', methods=['GET'])
def get_notes():
    patient_name = request.args.get('name')
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
    # Use environment port for Render, default to 5001 locally
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', debug=True, port=port)
