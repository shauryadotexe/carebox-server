from flask import Flask, request, jsonify
import csv
import os
import uuid

ACTIVE_CALL_URL = None

DATA_FILE = 'patient_data.csv'

app = Flask(__name__)

@app.route('/start_call', methods=['GET'])
def start_call():
    global ACTIVE_CALL_URL

    room_id = "CareBox-Call-" + str(uuid.uuid4())[:8]
    room_url = f"https://meet.jit.si/{room_id}"

    ACTIVE_CALL_URL = room_url

    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"DOCTOR: A patient is calling. Join this room:")
    print(f"{room_url}")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    return jsonify({"url": room_url})

@app.route('/get_active_call', methods=['GET'])
def get_active_call():
    global ACTIVE_CALL_URL
    
    if ACTIVE_CALL_URL:
        url_to_send = ACTIVE_CALL_URL
        
        ACTIVE_CALL_URL = None 
        
        return jsonify({"url": url_to_send})
    else:
        return jsonify({"url": None})

@app.route('/submit_patient', methods=['POST'])
def handle_patient_submission():
    
    data = request.json
    
    print(f"--- SERVER RECEIVED DATA ---")
    print(f"Name: {data.get('name')}")
    print(f"Age:  {data.get('age')}")
    print(f"Gender:  {data.get('sex')}") 
    print("----------------------------")
    
    file_exists = os.path.isfile(DATA_FILE)
    
    try:
        with open(DATA_FILE, mode='a', newline='') as file:
            fieldnames = ['name', 'age', 'sex']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data)
            
        print("...Data saved to patient_data.csv")
        return jsonify({"status": "success", "message": "Data received and saved!"})
    
    except Exception as e:
        print(f"!!! SERVER ERROR: Could not save data. {e}")
        return jsonify({"status": "error", "message": "Server failed to save data"}), 500
    
@app.route('/get_notes', methods=['GET'])
def get_notes():
    """
    Gets the notes for a specific patient.
    """
    patient_name = request.args.get('name')
    if not patient_name:
        return jsonify({"error": "A 'name' parameter is required."}), 400

    filepath = os.path.join("patient_notes", f"{patient_name}.txt")

    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                notes = f.read()
            return jsonify({"notes": notes})
        else:
            # It's a new patient, return blank notes
            return jsonify({"notes": ""})
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": "Could not read notes"}), 500

# --- AND ADD THIS NEW FUNCTION ---
@app.route('/update_notes', methods=['POST'])
def update_notes():
    """
    Saves new notes for a specific patient.
    """
    data = request.json
    patient_name = data.get('name')
    notes = data.get('notes')

    if not patient_name or notes is None:
        return jsonify({"error": "Name and notes are required."}), 400

    filepath = os.path.join("patient_notes", f"{patient_name}.txt")

    try:
        with open(filepath, 'w') as f:
            f.write(notes)
        return jsonify({"status": "success", "message": "Notes saved."})
    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"error": "Could not save notes"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0')
