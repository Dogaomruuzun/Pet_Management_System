from flask import Flask, request, jsonify, send_from_directory
import pickle, uuid, json, os
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATA_FILE = "data.json"
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global storage
users = []
pets = []
medical_history = []
vaccines = []
weights = []
appointments = []

def load_data():
    global users, pets, medical_history, vaccines, weights, appointments
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                users = data.get("users", [])
                pets = data.get("pets", [])
                medical_history = data.get("medical_history", [])
                vaccines = data.get("vaccines", [])
                weights = data.get("weights", [])
                appointments = data.get("appointments", [])
        except Exception as e:
            print(f"Error loading data: {e}")
            users, pets, medical_history, vaccines, weights, appointments = [], [], [], [], [], []
    else:
        # Initialize empty if no file
        users, pets, medical_history, vaccines, weights, appointments = [], [], [], [], [], []

def save_data():
    data = {
        "users": users,
        "pets": pets,
        "medical_history": medical_history,
        "vaccines": vaccines,
        "weights": weights,
        "appointments": appointments
    }
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

# Load data immediately
load_data()

try:
    lifespan_model = pickle.load(open("model/lifespan_model.pkl", "rb"))
    health_model = pickle.load(open("model/health_model.pkl", "rb"))
    breed_model = pickle.load(open("model/breed_model.pkl", "rb"))
except:
    lifespan_model = None
    health_model = None
    breed_model = None

def generate_id():
    return str(uuid.uuid4())

# -------------------- AUTH --------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    for u in users:
        if u["email"] == data["email"]:
            return jsonify({"error": "User already exists"}), 400

    user = {
        "id": generate_id(),
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "role": "vet" # Enforce Vets only via public register
    }
    users.append(user)
    save_data()
    return jsonify(user)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    for u in users:
        if u["email"] == data["email"] and u["password"] == data["password"]:
            return jsonify({"status": "ok", "user": u})
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route("/users", methods=["GET"])
def get_users():
    return jsonify(users) # Return full objects for internal vet usage

# -------------------- OWNERS (Vet Managed) --------------------

@app.route("/owner/add", methods=["POST"])
def add_owner():
    data = request.json
    # Owners are users with role 'owner'
    user = {
        "id": data.get("id") if data.get("id") else generate_id(),
        "name": data["name"],
        "email": data.get("email", ""), # Optional/generated
        "password": "123", # Default password
        "role": "owner",
        "phone": data.get("phone", ""),
        "address": data.get("address", "")
    }
    users.append(user)
    save_data()
    return jsonify(user)

@app.route("/owner/edit", methods=["POST"])
def edit_owner():
    data = request.json
    for u in users:
        if u["id"] == data["id"]:
            u.update(data)
            save_data()
            return jsonify(u)
    return jsonify({"error": "not found"})

@app.route("/owner/delete", methods=["POST"])
def delete_owner():
    data = request.json
    uid = data["id"]
    for u in users:
        if u["id"] == uid:
            users.remove(u)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"})

# -------------------- UPLOADS --------------------

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        ext = file.filename.split('.')[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        url = f"http://127.0.0.1:5000/uploads/{filename}"
        return jsonify({"url": url})

# -------------------- PETS --------------------

@app.route("/add_pet", methods=["POST"])
def add_pet():
    data = request.json
    pet = {
        "id": generate_id(),
        "name": data["name"],
        "age": data["age"],
        "type": data["type"],
        "photo": data["photo"],
        "ownerId": data["ownerId"]
    }
    pets.append(pet)
    save_data()
    return jsonify(pet)

@app.route("/pets", methods=["GET"])
def get_pets():
    return jsonify(pets)

@app.route("/edit_pet", methods=["POST"])
def edit_pet():
    data = request.json
    for p in pets:
        if p["id"] == data["id"]:
            p.update(data)
            save_data()
            return jsonify(p)
    return jsonify({"error": "not found"})

@app.route("/delete_pet", methods=["POST"])
def delete_pet():
    data = request.json
    pet_id = data["id"]
    for p in pets:
        if p["id"] == pet_id:
            pets.remove(p)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"status": "not_found"})

# -------------------- MEDICAL HISTORY --------------------

@app.route("/medical/add", methods=["POST"])
def add_medical():
    data = request.json
    rec = {
        "id": generate_id(),
        "petId": data["petId"],
        "date": data["date"],
        "diagnosis": data["diagnosis"],
        "treatment": data["treatment"],
        "notes": data["notes"],
        "attachment": data["attachment"]
    }
    medical_history.append(rec)
    save_data()
    return jsonify(rec)

@app.route("/medical/<pet_id>", methods=["GET"])
def get_medical(pet_id):
    result = [m for m in medical_history if m["petId"] == pet_id]
    return jsonify(result)

@app.route("/medical/edit", methods=["POST"])
def edit_medical():
    data = request.json
    for m in medical_history:
        if m["id"] == data["id"]:
            m.update(data)
            save_data()
            return jsonify(m)
    return jsonify({"error": "not found"})

@app.route("/medical/delete", methods=["POST"])
def delete_medical():
    data = request.json
    doc_id = data["id"]
    for m in medical_history:
        if m["id"] == doc_id:
            medical_history.remove(m)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"})

# -------------------- VACCINES --------------------

@app.route("/vaccine/add", methods=["POST"])
def add_vaccine():
    data = request.json
    rec = {
        "id": generate_id(),
        "petId": data["petId"],
        "vaccineName": data["vaccineName"],
        "dateGiven": data["dateGiven"],
        "nextDue": data["nextDue"]
    }
    vaccines.append(rec)
    save_data()
    return jsonify(rec)

@app.route("/vaccine/<pet_id>", methods=["GET"])
def get_vaccines(pet_id):
    result = [v for v in vaccines if v["petId"] == pet_id]
    return jsonify(result)

@app.route("/vaccine/edit", methods=["POST"])
def edit_vaccine():
    data = request.json
    for v in vaccines:
        if v["id"] == data["id"]:
            v.update(data)
            save_data()
            return jsonify(v)
    return jsonify({"error": "not found"})

@app.route("/vaccine/delete", methods=["POST"])
def delete_vaccine():
    data = request.json
    doc_id = data["id"]
    for v in vaccines:
        if v["id"] == doc_id:
            vaccines.remove(v)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"})

# -------------------- WEIGHT --------------------

@app.route("/weight/add", methods=["POST"])
def add_weight():
    data = request.json
    rec = {
        "id": generate_id(),
        "petId": data["petId"],
        "weight": data["weight"],
        "date": data["date"]
    }
    weights.append(rec)
    save_data()
    return jsonify(rec)

@app.route("/weight/<pet_id>", methods=["GET"])
def get_weight(pet_id):
    result = [w for w in weights if w["petId"] == pet_id]
    return jsonify(result)

@app.route("/weight/edit", methods=["POST"])
def edit_weight():
    data = request.json
    for w in weights:
        if w["id"] == data["id"]:
            w.update(data)
            save_data()
            return jsonify(w)
    return jsonify({"error": "not found"})

@app.route("/weight/delete", methods=["POST"])
def delete_weight():
    data = request.json
    doc_id = data["id"]
    for w in weights:
        if w["id"] == doc_id:
            weights.remove(w)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"})

# -------------------- APPOINTMENTS --------------------

@app.route("/appointment/add", methods=["POST"])
def add_appointment():
    data = request.json
    rec = {
        "id": generate_id(),
        "petId": data["petId"],
        "date": data["date"],
        "time": data["time"],
        "reason": data["reason"],
        "vetId": data["vetId"]
    }
    appointments.append(rec)
    save_data()
    return jsonify(rec)

@app.route("/appointment/<pet_id>", methods=["GET"])
def get_appointment(pet_id):
    result = [a for a in appointments if a["petId"] == pet_id]
    return jsonify(result)

@app.route("/appointment/edit", methods=["POST"])
def edit_appointment():
    data = request.json
    for a in appointments:
        if a["id"] == data["id"]:
            a.update(data)
            save_data()
            return jsonify(a)
    return jsonify({"error": "not found"})

@app.route("/appointment/delete", methods=["POST"])
def delete_appointment():
    data = request.json
    doc_id = data["id"]
    for a in appointments:
        if a["id"] == doc_id:
            appointments.remove(a)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"})

# -------------------- AI MODULES --------------------

@app.route("/ai/lifespan", methods=["POST"])
def ai_lifespan():
    if lifespan_model is None:
        return jsonify({"error": "model not loaded"})
    age = request.json["age"]
    pred = lifespan_model.predict([[age]])[0]
    return jsonify({"prediction": float(pred)})

@app.route("/ai/health_score", methods=["POST"])
def ai_health():
    if health_model is None:
        return jsonify({"error": "model not loaded"})
    x = [[request.json["age"], request.json["weight"]]]
    pred = health_model.predict(x)[0]
    return jsonify({"prediction": float(pred)})

@app.route("/ai/breed_risk", methods=["POST"])
def ai_breed():
    if breed_model is None:
        return jsonify({"error": "model not loaded"})
    x = [[request.json["age"]]]
    pred = breed_model.predict(x)[0]
    return jsonify({"prediction": pred})

if __name__ == "__main__":
    app.run(debug=True)

