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
    
    if not os.path.exists(CREDENTIALS_FILE):
        return jsonify({"success": False}), 500
            
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            valid_users = json.load(f)
            
        if username in valid_users and valid_users[username] == password:
            return jsonify({"success": True, "message": "Access Granted"})
        else:
            return jsonify({"success": False, "message": "Invalid Credentials"}), 401
    except:
        return jsonify({"success": False}), 500

# --- 2. CALL HANDLING ---
@app.route('/start_call', methods=['GET'])
def start_call():
    global ACTIVE_CALL
    patient_name = request.args.get('patient_name')
    room_id = "CareBox-Call-" + str(uuid.uuid4())[:8]
    room_url = f"https://meet.jit.si/{room_id}"
    ACTIVE_CALL = {"url": room_url, "patient_name": patient_name}
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

# --- 3. PATIENT DATA (IMPROVED) ---
@app.route('/submit_patient', methods=['POST'])
def handle_patient_submission():
    data = request.json
    data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    file_exists = os.path.isfile(DATA_FILE)
    try:
        with open(DATA_FILE, mode='a', newline='') as file:
            fieldnames = ['name', 'age', 'sex', 'timestamp']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists: writer.writeheader()
            writer.writerow(data)
        return jsonify({"status": "success"})
    except:
        return jsonify({"status": "error"}), 500

# *** NEW SEARCH ENDPOINT ***
@app.route('/search_patients', methods=['GET'])
def search_patients():
    query = request.args.get('query', '').lower()
    matches = []
    
    if not os.path.exists(DATA_FILE):
        return jsonify([])
        
    try:
        with open(DATA_FILE, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # If query is empty, show everyone, otherwise filter
                if not query or query in row['name'].lower():
                    matches.append(row)
        return jsonify(matches)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 4. NOTES & CHAT ---
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
    new_note = data.get('notes')
    
    if not os.path.exists("patient_notes"): os.makedirs("patient_notes")
    filepath = os.path.join("patient_notes", f"{patient_name}.txt")
    
    # Auto-timestamp the note
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
    entry = f"{timestamp}\n{new_note}\n{'-'*20}\n"
    
    # Append to file instead of overwriting
    with open(filepath, 'a') as f: 
        f.write(entry)
        
    return jsonify({"status": "success"})

@app.route('/clear_notes', methods=['POST'])
def clear_notes():
    data = request.json
    name = data.get('name')
    if not name: return jsonify({"error": "No name provided"}), 400
    
    if not os.path.exists("patient_notes"):
        return jsonify({"status": "no_files"})
        
    filepath = os.path.join("patient_notes", f"{name}.txt")
    try:
        # Open in 'w' mode and write nothing to clear it
        with open(filepath, 'w') as f:
            f.write("")
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 5. SCAN DATA: patient -> server -> doctor ---
@app.route('/submit_scan_data', methods=['POST'])
def submit_scan_data():
    data = request.json or {}
    patient_name = data.get('patient_name', 'Unknown')
    timestamp = data.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    scans_dir = 'scans'
    if not os.path.exists(scans_dir): os.makedirs(scans_dir)

    filename = f"{patient_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    try:
        with open(os.path.join(scans_dir, filename), 'w') as f:
            json.dump(data, f)
        return jsonify({"status": "success", "file": filename})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/get_scans', methods=['GET'])
def get_scans():
    scans_dir = 'scans'
    if not os.path.exists(scans_dir):
        return jsonify([])
    files = sorted(os.listdir(scans_dir), reverse=True)
    out = []
    for fn in files:
        path = os.path.join(scans_dir, fn)
        try:
            with open(path, 'r') as f:
                payload = json.load(f)
            out.append({
                'file': fn,
                'patient_name': payload.get('patient_name'),
                'timestamp': payload.get('timestamp', fn.split('_')[-1].replace('.json',''))
            })
        except:
            continue
    return jsonify(out)

@app.route('/get_scan', methods=['GET'])
def get_scan():
    filename = request.args.get('file')
    if not filename:
        return jsonify({"error": "no file specified"}), 400
    path = os.path.join('scans', filename)
    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404
    try:
        with open(path, 'r') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chat routes (omitted for brevity, keep existing ones) ...
# View Logs route (keep existing one) ...

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', debug=True, port=port)
