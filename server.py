from flask import Flask, request, jsonify
import csv
import os
import uuid

# --- Global variable to store the call URL ---
ACTIVE_CALL_URL = None

DATA_FILE = 'patient_data.csv'

# --- 1. ONLY CREATE ONE APP ---
app = Flask(__name__)

# --- 2. This route is for the PATIENT ---
@app.route('/start_call', methods=['GET'])
def start_call():
    global ACTIVE_CALL_URL

    room_id = "CareBox-Call-" + str(uuid.uuid4())[:8]
    room_url = f"https://meet.jit.si/{room_id}"

    # Save the URL so the doctor can get it
    ACTIVE_CALL_URL = room_url

    # Print notification to the server terminal
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"DOCTOR: A patient is calling. Join this room:")
    print(f"{room_url}")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    # Send the URL back to the patient's app
    return jsonify({"url": room_url})

# --- 3. This route is for the DOCTOR ---
@app.route('/get_active_call', methods=['GET'])
def get_active_call():
    global ACTIVE_CALL_URL
    
    if ACTIVE_CALL_URL:
        url_to_send = ACTIVE_CALL_URL
        
        # Clear the URL after giving it to the doctor
        ACTIVE_CALL_URL = None 
        
        return jsonify({"url": url_to_send})
    else:
        # No call waiting
        return jsonify({"url": None})

# --- 4. This route is for the PATIENT's initial data ---
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

# --- 5. RUN THE APP ---
if __name__ == '__main__':
    # Make sure to run 'app', not 'server'
    app.run(host='0.0.0.0')