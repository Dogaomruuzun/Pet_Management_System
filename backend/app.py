from flask import Flask, request, jsonify, send_from_directory, session, redirect
import pickle, uuid, json, os
from flask_cors import CORS


# -------------------- PATHS --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
MODEL_DIR = os.path.join(BASE_DIR, "model")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

# Serve the front-end from Flask (so you can open http://127.0.0.1:5000/)
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.secret_key = "dev-secret-key"
CORS(app, supports_credentials=True)


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -------------------- IN-MEMORY STORAGE --------------------
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
            with open(DATA_FILE, "r", encoding="utf-8") as f:
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
        users, pets, medical_history, vaccines, weights, appointments = [], [], [], [], [], []


def save_data():
    data = {
        "users": users,
        "pets": pets,
        "medical_history": medical_history,
        "vaccines": vaccines,
        "weights": weights,
        "appointments": appointments,
    }
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")


load_data()

# -------------------- LOAD AI MODELS --------------------

def _load_model(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Failed to load model {path}: {e}")
        return None


lifespan_model = _load_model(os.path.join(MODEL_DIR, "lifespan_model.pkl"))
health_model = _load_model(os.path.join(MODEL_DIR, "health_model.pkl"))
breed_model = _load_model(os.path.join(MODEL_DIR, "breed_model.pkl"))


diagnose_vectorizer = _load_model(os.path.join(MODEL_DIR, "diagnose_vectorizer.pkl"))
diagnose_model = _load_model(os.path.join(MODEL_DIR, "diagnose_model.pkl"))


def generate_id():
    return str(uuid.uuid4())


# -------------------- FRONTEND --------------------



@app.get("/")
def root():
   
    return app.send_static_file("index.html")





# -------------------- AUTH --------------------
@app.post("/register")
def register():
    data = request.json or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    for u in users:
        if u.get("email") == email:
            return jsonify({"error": "User already exists"}), 400

    user = {
        "id": generate_id(),
        "name": name,
        "email": email,
        "password": password,
        "role": "vet",
    }

    users.append(user)
    save_data()

    # login after register
    session["user_id"] = user["id"]

    return jsonify({"status": "ok", "user": user})


@app.post("/login")
def login():
    data = request.json or {}

    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    for u in users:
        if u.get("email") == email and u.get("password") == password:
            session["user_id"] = u["id"]   # <-- sadece doğruysa burada set
            return jsonify({"status": "ok", "user": u})

    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.post("/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok"})

@app.get("/users")
def get_users():
    return jsonify(users)

@app.get("/me")
def me():
    return jsonify({"user_id": session.get("user_id")})


# -------------------- OWNERS (Vet Managed) --------------------

@app.post("/owner/add")
def add_owner():
    data = request.json or {}
    user = {
        "id": data.get("id") or generate_id(),
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "password": "123",  # default
        "role": "owner",
        "phone": data.get("phone", ""),
        "address": data.get("address", ""),
    }
    if not user["id"] or not user["name"]:
        return jsonify({"error": "ID and Name are required"}), 400

    users.append(user)
    save_data()
    return jsonify(user)


@app.post("/owner/edit")
def edit_owner():
    data = request.json or {}
    for u in users:
        if u.get("id") == data.get("id"):
            u.update(data)
            save_data()
            return jsonify(u)
    return jsonify({"error": "not found"}), 404


@app.post("/owner/delete")
def delete_owner():
    data = request.json or {}
    uid = data.get("id")
    for u in list(users):
        if u.get("id") == uid:
            users.remove(u)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404


# -------------------- UPLOADS --------------------

@app.get("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.post("/upload")
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # For local dev; if you deploy, change host accordingly.
    url = f"http://127.0.0.1:5000/uploads/{filename}"
    return jsonify({"url": url})


# -------------------- PETS --------------------

@app.post("/add_pet")
def add_pet():
    data = request.json or {}
    pet = {
        "id": generate_id(),
        "name": data.get("name", ""),
        "age": data.get("age", 0),
        "type": data.get("type", ""),
        "photo": data.get("photo", ""),
        "ownerId": data.get("ownerId", ""),
    }
    if not pet["name"] or pet["photo"] is None:
        return jsonify({"error": "Missing fields"}), 400

    pets.append(pet)
    save_data()
    return jsonify(pet)


@app.get("/pets")
def get_pets():
    return jsonify(pets)


@app.post("/edit_pet")
def edit_pet():
    data = request.json or {}
    for p in pets:
        if p.get("id") == data.get("id"):
            p.update(data)
            save_data()
            return jsonify(p)
    return jsonify({"error": "not found"}), 404


@app.post("/delete_pet")
def delete_pet():
    data = request.json or {}
    pet_id = data.get("id")
    for p in list(pets):
        if p.get("id") == pet_id:
            pets.remove(p)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"status": "not_found"}), 404


# -------------------- MEDICAL HISTORY --------------------

@app.post("/medical/add")
def add_medical():
    data = request.json or {}
    rec = {
        "id": generate_id(),
        "petId": data.get("petId"),
        "date": data.get("date"),
        "diagnosis": data.get("diagnosis"),
        "treatment": data.get("treatment"),
        "notes": data.get("notes", ""),
        "attachment": data.get("attachment", ""),
    }
    medical_history.append(rec)
    save_data()
    return jsonify(rec)


@app.get("/medical/<pet_id>")
def get_medical(pet_id):
    result = [m for m in medical_history if m.get("petId") == pet_id]
    return jsonify(result)


@app.post("/medical/edit")
def edit_medical():
    data = request.json or {}
    for m in medical_history:
        if m.get("id") == data.get("id"):
            m.update(data)
            save_data()
            return jsonify(m)
    return jsonify({"error": "not found"}), 404


@app.post("/medical/delete")
def delete_medical():
    data = request.json or {}
    doc_id = data.get("id")
    for m in list(medical_history):
        if m.get("id") == doc_id:
            medical_history.remove(m)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404


# -------------------- VACCINES --------------------

@app.post("/vaccine/add")
def add_vaccine():
    data = request.json or {}
    rec = {
        "id": generate_id(),
        "petId": data.get("petId"),
        "vaccineName": data.get("vaccineName"),
        "dateGiven": data.get("dateGiven"),
        "nextDue": data.get("nextDue"),
    }
    vaccines.append(rec)
    save_data()
    return jsonify(rec)


@app.get("/vaccine/<pet_id>")
def get_vaccines(pet_id):
    result = [v for v in vaccines if v.get("petId") == pet_id]
    return jsonify(result)


@app.post("/vaccine/edit")
def edit_vaccine():
    data = request.json or {}
    for v in vaccines:
        if v.get("id") == data.get("id"):
            v.update(data)
            save_data()
            return jsonify(v)
    return jsonify({"error": "not found"}), 404


@app.post("/vaccine/delete")
def delete_vaccine():
    data = request.json or {}
    doc_id = data.get("id")
    for v in list(vaccines):
        if v.get("id") == doc_id:
            vaccines.remove(v)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404


# -------------------- WEIGHT --------------------

@app.post("/weight/add")
def add_weight():
    data = request.json or {}
    rec = {
        "id": generate_id(),
        "petId": data.get("petId"),
        "weight": data.get("weight"),
        "date": data.get("date"),
    }
    weights.append(rec)
    save_data()
    return jsonify(rec)


@app.get("/weight/<pet_id>")
def get_weight(pet_id):
    result = [w for w in weights if w.get("petId") == pet_id]
    return jsonify(result)


@app.post("/weight/edit")
def edit_weight():
    data = request.json or {}
    for w in weights:
        if w.get("id") == data.get("id"):
            w.update(data)
            save_data()
            return jsonify(w)
    return jsonify({"error": "not found"}), 404


@app.post("/weight/delete")
def delete_weight():
    data = request.json or {}
    doc_id = data.get("id")
    for w in list(weights):
        if w.get("id") == doc_id:
            weights.remove(w)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404


# -------------------- APPOINTMENTS --------------------

@app.post("/appointment/add")
def add_appointment():
    data = request.json or {}
    rec = {
        "id": generate_id(),
        "petId": data.get("petId"),
        "date": data.get("date"),
        "time": data.get("time"),
        "reason": data.get("reason"),
        "vetId": data.get("vetId"),
    }
    appointments.append(rec)
    save_data()
    return jsonify(rec)


@app.get("/appointment/<pet_id>")
def get_appointment(pet_id):
    result = [a for a in appointments if a.get("petId") == pet_id]
    return jsonify(result)


@app.post("/appointment/edit")
def edit_appointment():
    data = request.json or {}
    for a in appointments:
        if a.get("id") == data.get("id"):
            a.update(data)
            save_data()
            return jsonify(a)
    return jsonify({"error": "not found"}), 404


@app.post("/appointment/delete")
def delete_appointment():
    data = request.json or {}
    doc_id = data.get("id")
    for a in list(appointments):
        if a.get("id") == doc_id:
            appointments.remove(a)
            save_data()
            return jsonify({"status": "ok"})
    return jsonify({"error": "not found"}), 404


# -------------------- AI MODULES --------------------

@app.post("/ai/lifespan")
def ai_lifespan():
    if lifespan_model is None:
        return jsonify({"error": "model not loaded. Run: python train_models.py"}), 500

    age = request.json.get("age") if request.json else None
    if age is None:
        return jsonify({"error": "age is required"}), 400

    pred = lifespan_model.predict([[float(age)]])[0]
    return jsonify({"prediction": float(pred)})


@app.post("/ai/health_score")
def ai_health():
    if health_model is None:
        return jsonify({"error": "model not loaded. Run: python train_models.py"}), 500

    body = request.json or {}
    age = body.get("age")
    weight = body.get("weight")
    if age is None or weight is None:
        return jsonify({"error": "age and weight are required"}), 400

    x = [[float(age), float(weight)]]
    pred = health_model.predict(x)[0]
    return jsonify({"prediction": float(pred)})


@app.post("/ai/breed_risk")
def ai_breed():
    if breed_model is None:
        return jsonify({"error": "model not loaded. Run: python train_models.py"}), 500

    age = request.json.get("age") if request.json else None
    if age is None:
        return jsonify({"error": "age is required"}), 400

    x = [[float(age)]]
    pred = breed_model.predict(x)[0]
    return jsonify({"prediction": str(pred)})


@app.route("/ai/diagnose", methods=["POST"])
def ai_diagnose():
    """Very lightweight symptom -> condition estimator.

    IMPORTANT: This is NOT a veterinary diagnosis. It is an educational estimate
    based on a small synthetic training set.
    """
    if diagnose_model is None or diagnose_vectorizer is None:
        return jsonify({"error": "diagnosis model not loaded. Run: python3 train_models.py"}), 400

    data = request.json or {}
    symptoms = (data.get("symptoms") or "").strip()
    species = (data.get("species") or "").strip()
    age = data.get("age", None)

    if not symptoms:
        return jsonify({"error": "symptoms is required"}), 400

    # Combine species/age into text to provide tiny context
    parts = []
    if species:
        parts.append(species)
    if age is not None:
        parts.append(f"age {age}")
    parts.append(symptoms)
    text = " ".join(parts)

    X = diagnose_vectorizer.transform([text])
    probs = diagnose_model.predict_proba(X)[0]
    classes = list(diagnose_model.classes_)

    # top3
    top_idx = sorted(range(len(probs)), key=lambda i: float(probs[i]), reverse=True)[:3]
    top3 = [{"label": classes[i], "prob": float(probs[i])} for i in top_idx]

    best_i = top_idx[0]
    diagnosis = classes[best_i]
    confidence = float(probs[best_i])

    notes = {
        "Gastroenteritis": "Common signs include vomiting/diarrhea. Watch hydration. If severe, persistent, or there is blood, consult a vet urgently.",
        "Upper Respiratory Infection": "Coughing/sneezing can be mild or contagious. If breathing is difficult, fever is high, or symptoms persist, consult a vet.",
        "Ear Infection": "Ear pain/odor/discharge often needs proper treatment. Avoid putting random drops; consult a vet for the right medication.",
        "Fleas / Skin Irritation": "Itching and hair loss can be fleas or allergies. Use safe flea control and check bedding. If skin is red/raw, consult a vet.",
        "Arthritis / Joint Pain": "Stiffness/limping can indicate joint pain. Avoid heavy exercise. If limping lasts >24-48h, consult a vet.",
        "Diabetes Warning": "Excess thirst/urination and weight loss can be serious. A vet visit for blood/urine tests is recommended.",
    }

    return jsonify({
        "diagnosis": diagnosis,
        "confidence": confidence,
        "top3": top3,
        "note": notes.get(diagnosis, ""),
        "disclaimer": "Educational only — not a diagnosis. For urgent symptoms (breathing trouble, seizures, collapse, severe pain, continuous vomiting/diarrhea, blood), seek veterinary care immediately."
    })


# Optional aliases (in case you used /api/... in testing)
@app.route("/api/ai/predict_lifespan", methods=["POST"])
def api_predict_lifespan():
    return ai_lifespan()

@app.route("/api/ai/predict_health", methods=["POST"])
def api_predict_health():
    return ai_health()

@app.route("/api/ai/predict_breed_risk", methods=["POST"])
def api_predict_breed_risk():
    return ai_breed()

if __name__ == "__main__":
    app.run(debug=True)
