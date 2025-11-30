from flask import Flask, request, jsonify
import pickle, uuid
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

try:
    lifespan_model = pickle.load(open("model/lifespan_model.pkl", "rb"))
    health_model = pickle.load(open("model/health_model.pkl", "rb"))
    breed_model = pickle.load(open("model/breed_model.pkl", "rb"))
except:
    lifespan_model = None
    health_model = None
    breed_model = None

users = []
pets = []
medical_history = []
vaccines = []
weights = []
appointments = []

def generate_id():
    return str(uuid.uuid4())

# -------------------- AUTH --------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    user = {
        "id": generate_id(),
        "name": data["name"],
        "email": data["email"],
        "password": data["password"],
        "role": data["role"]
    }
    users.append(user)
    return jsonify(user)

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    for u in users:
        if u["email"] == data["email"] and u["password"] == data["password"]:
            return jsonify({"status": "ok", "user": u})
    return jsonify({"status": "error"})

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
            return jsonify(p)
    return jsonify({"error": "not found"})

@app.route("/delete_pet", methods=["POST"])
def delete_pet():
    data = request.json
    pet_id = data["id"]
    for p in pets:
        if p["id"] == pet_id:
            pets.remove(p)
            return jsonify({"status": "ok"})
    return jsonify({"status": "not_found"})

# -------------------- OWNER INFO --------------------

@app.route("/owner/<owner_id>", methods=["GET"])
def get_owner(owner_id):
    result = [p for p in pets if p["ownerId"] == owner_id]
    return jsonify(result)

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
    return jsonify(rec)

@app.route("/medical/<pet_id>", methods=["GET"])
def get_medical(pet_id):
    result = [m for m in medical_history if m["petId"] == pet_id]
    return jsonify(result)

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
    return jsonify(rec)

@app.route("/vaccine/<pet_id>", methods=["GET"])
def get_vaccines(pet_id):
    result = [v for v in vaccines if v["petId"] == pet_id]
    return jsonify(result)

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
    return jsonify(rec)

@app.route("/weight/<pet_id>", methods=["GET"])
def get_weight(pet_id):
    result = [w for w in weights if w["petId"] == pet_id]
    return jsonify(result)

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
    return jsonify(rec)

@app.route("/appointment/<pet_id>", methods=["GET"])
def get_appointment(pet_id):
    result = [a for a in appointments if a["petId"] == pet_id]
    return jsonify(result)

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
