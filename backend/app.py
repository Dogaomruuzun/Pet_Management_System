from flask import Flask, request, jsonify, send_from_directory, session, redirect
import pickle, uuid, json, os
from flask_cors import CORS


# -------------------- PATHS --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
import sys
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from db import init_db as db_init, fetch_all as db_fetch_all, replace_all as db_replace_all, DB_FILE
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
    """Populate in-memory lists from SQLite (and migrate from data.json if present)."""
    global users, pets, medical_history, vaccines, weights, appointments
    try:
        # Ensure DB and schema exist
        db_init()

        data = db_fetch_all()
        # If DB is empty but a legacy JSON file exists, migrate it
        if not any(data.values()) and os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                for k in ["users", "pets", "medical_history", "vaccines", "weights", "appointments"]:
                    json_data.setdefault(k, [])
                db_replace_all(json_data)
                data = db_fetch_all()
                print("Migrated legacy data.json into SQLite:", DB_FILE)
            except Exception as e:
                print(f"Error migrating data.json to DB: {e}")

        users = data.get("users", [])
        pets = data.get("pets", [])
        medical_history = data.get("medical_history", [])
        vaccines = data.get("vaccines", [])
        weights = data.get("weights", [])
        appointments = data.get("appointments", [])
    except Exception as e:
        print(f"Error initializing/loading DB: {e}")
        # Fallback to legacy JSON only if DB access fails entirely
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
            except Exception as e2:
                print(f"Error loading legacy JSON: {e2}")
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
    # Persist to SQLite
    try:
        db_init()
        db_replace_all(data)
    except Exception as e:
        print(f"Error saving to DB: {e}")
    # Keep writing legacy JSON as a backup for now
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving legacy JSON: {e}")


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


# -------------------- LLM (FLAN-T5 veterinary QA) --------------------
_vet_llm_pipe = None
_vet_llm_device = "cpu"
import threading
_vet_llm_lock = threading.Lock()


def get_vet_llm_pipeline():
    global _vet_llm_pipe
    if _vet_llm_pipe is not None:
        return _vet_llm_pipe
    with _vet_llm_lock:
        if _vet_llm_pipe is not None:
            return _vet_llm_pipe
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

            model_name = os.environ.get(
                "VET_QA_MODEL", "ahmed807762/flan-t5-base-veterinaryQA_data-v2"
            )

            # Force CPU unless explicitly overridden
            device = "cuda" if (hasattr(torch, "cuda") and torch.cuda.is_available()) else "cpu"
            if os.environ.get("VET_QA_FORCE_CPU", "1") == "1":
                device = "cpu"

            tok = AutoTokenizer.from_pretrained(model_name)

            def _load_model():
                try:
                    return AutoModelForSeq2SeqLM.from_pretrained(
                        model_name,
                        dtype=torch.float32,
                        low_cpu_mem_usage=False,
                    )
                except TypeError:
                    # Older transformers
                    return AutoModelForSeq2SeqLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=False,
                    )

            mdl = _load_model()
            mdl.eval()

            # pipeline device: -1 for CPU, GPU index for CUDA
            device_arg = -1 if device == "cpu" else 0
            _pipe = pipeline(
                "text2text-generation",
                model=mdl,
                tokenizer=tok,
                device=device_arg,
                framework="pt",
            )
            print(f"Device set to use {device}")
            print(f"Loaded veterinary QA model: {model_name}")

            # Save globals
            global _vet_llm_device
            _vet_llm_device = device
            _vet_llm_pipe = _pipe
            return _vet_llm_pipe
        except Exception as e:
            print(f"Failed to load veterinary QA model: {e}")
            _vet_llm_pipe = None
            return None


# Optional: warm-up the LLM in background so first request is faster
def _warmup_llm_async():
    try:
        import threading

        def _task():
            pipe = get_vet_llm_pipeline()
            if pipe is None:
                return
            try:
                pipe("Warmup question: Provide one word.", max_new_tokens=8)
            except Exception:
                pass

        if os.environ.get("VET_QA_WARMUP", "1") == "1":
            threading.Thread(target=_task, daemon=True).start()
    except Exception:
        pass

_warmup_llm_async()


# -------------------- Rule-based fallback for suggestions --------------------

def _species_group(name: str) -> str:
    s = (name or "").strip().lower()
    small = {"hamster", "guinea pig", "guinea-pig", "rabbit", "bunny", "gerbil", "rat", "mouse", "mice", "chinchilla"}
    birds = {"bird", "parrot", "budgie", "budgerigar", "cockatiel", "finch"}
    reptiles = {"reptile", "turtle", "tortoise", "snake", "lizard", "gecko", "bearded dragon"}
    if s in small or any(k in s for k in ["hamster", "guinea", "rabbit", "gerbil", "rat", "mouse", "chinch"]):
        return "small_mammal"
    if s in birds or any(k in s for k in ["parrot", "budg", "cockatiel", "finch", "bird"]):
        return "bird"
    if s in reptiles or any(k in s for k in ["turtle", "tortoise", "snake", "lizard", "gecko", "dragon"]):
        return "reptile"
    if any(k in s for k in ["dog", "cat", "canine", "feline"]):
        return "dogcat"
    return "other"


def _fallback_suggestions(species: str, age, symptoms: str):
    text = (symptoms or "").lower()
    grp = _species_group(species)
    conds = []
    reds = []
    care = []

    def add_cond(name, reason):
        if len(conds) < 3:
            conds.append({"name": name, "reason": reason})

    # Common flags from symptoms
    lethargy = "letharg" in text or "tired" in text
    anorexia = "no appetite" in text or "not eating" in text or "reduced appetite" in text or "anorex" in text
    gi = any(k in text for k in ["vomit", "diarr", "stool", "poop", "constipat"])  # GI signs
    resp = any(k in text for k in ["cough", "sneez", "wheeze", "breath", "runny nose", "nasal"])  # respiratory
    pain = any(k in text for k in ["pain", "aggress", "hunch", "limp", "sore", "guard"])  # pain/behaviour
    # External wound/lameness keywords
    bleeding = any(k in text for k in ["bleed", "blood"]) and any(k in text for k in ["paw", "pad", "nail", "claw", "dewclaw", "toe", "foot", "leg"])
    paw_wound = any(k in text for k in ["paw", "pad", "nail", "claw", "dewclaw", "toe"]) and any(k in text for k in ["cut", "wound", "tear", "lacer", "broken", "rip"])
    lameness = any(k in text for k in ["limp", "non weight", "non-weight", "not weight", "not pressing", "holding up", "favoring", "not putting weight"]) or ("not pressing" in text)

    if grp == "small_mammal":
        if anorexia or lethargy or gi:
            add_cond("GI stasis/ileus", "Small mammals can stop eating from pain or stress; gut slows causing lethargy and anorexia")
        if pain or anorexia:
            add_cond("Dental disease", "Overgrown teeth cause mouth pain and reduced eating; common in hamsters/rodents")
        if resp:
            add_cond("Respiratory infection", "Sneezing/ocular-nasal discharge or effortful breathing suggests airway infection")
        if len(conds) == 0:
            add_cond("Stress or environmental issue", "Sudden change, overheating/cold, or enclosure problems can cause lethargy/anorexia")

        reds = [
            "Not eating/drinking > 24 hours",
            "Laboured or noisy breathing",
            "Severe abdominal bloating or profound weakness",
            "Blood in stool/urine or seizures",
        ]
        care = [
            "Keep warm, quiet, and minimize handling",
            "Offer familiar food and fresh water; do not force-feed if choking risk",
            "Check enclosure temperature and bedding; reduce stressors",
            "Arrange prompt exam — small mammals decline quickly",
        ]
    elif grp == "dogcat":
        # Prioritize external injuries when present
        if bleeding or paw_wound or lameness:
            add_cond("Torn/broken nail (quick injury)", "Bleeding from nail with reluctance to bear weight is typical")
            add_cond("Paw pad laceration or foreign body", "Blood on paw/pads; glass/thorns cause pain and non‑weight bearing")
            add_cond("Sprain/strain or fracture", "Lameness and guarding the limb after activity/trauma")
            reds = [
                "Bleeding that does not stop after 5–10 minutes of firm pressure",
                "Deep/dirty wound, bone visible, or nail partly avulsed",
                "Severe swelling, cold/blue toes, or non‑weight bearing",
            ]
            care = [
                "Apply gentle direct pressure with clean gauze for 5–10 minutes",
                "Rinse paw with saline/water to remove debris; avoid harsh chemicals",
                "Cover with a light bandage/sock; prevent licking (cone)",
                "Do NOT give human pain meds; arrange veterinary exam",
            ]
        else:
            if gi:
                add_cond("Gastroenteritis", "Vomiting/diarrhea with lethargy is consistent; monitor hydration")
            if pain or lethargy:
                add_cond("Pain or systemic illness", "Pain, fever, or endocrine disease can reduce appetite and activity")
            if resp:
                add_cond("Upper respiratory disease", "Cough/sneeze with malaise suggests airway infection/inflammation")
            if len(conds) == 0:
                add_cond("Non-specific illness", "Many conditions present with lethargy and anorexia — needs exam")
            reds = [
                "Continuous vomiting or diarrhea, or blood present",
                "Breathing difficulty, pale/blue gums",
                "Collapse, seizures, or severe pain",
            ]
            care = [
                "Provide water access; small frequent sips",
                "Withhold rich treats; bland diet if advised",
                "Seek vet care if symptoms persist >24–48h or any red flag",
            ]
    elif grp == "bird":
        add_cond("Respiratory infection", "Birds commonly mask illness until advanced; nasal discharge or effort is concerning")
        add_cond("Nutritional or husbandry issue", "Diet or temperature/air quality problems can cause lethargy and anorexia")
        add_cond("GI disease/parasites", "Soft stool/regurgitation with appetite changes suggests GI disease")
        reds = [
            "Open‑mouth breathing, tail bobbing",
            "Not eating for a day, fluffed and unresponsive",
            "Bleeding or fractures",
        ]
        care = [
            "Warm, quiet environment; reduce drafts",
            "Fresh water; offer familiar seed/pellets and soft foods",
            "Urgent avian vet exam if breathing changes or not eating",
        ]
    elif grp == "reptile":
        add_cond("Temperature/husbandry problem", "Incorrect heat/UVB often causes anorexia and lethargy")
        add_cond("GI or respiratory disease", "Mucus, wheeze, or abnormal stool indicate infection/parasites")
        add_cond("Nutritional deficiency", "Calcium/UVB problems lead to weakness and poor appetite")
        reds = [
            "Open‑mouth breathing, profound weakness",
            "Not eating >1–2 weeks in juveniles",
            "Neurologic signs or blood",
        ]
        care = [
            "Verify temperatures and UVB; provide proper basking gradient",
            "Offer appropriate prey/greens; ensure hydration",
            "Reptile‑experienced vet if no improvement",
        ]
    else:
        add_cond("Non‑specific illness", "Lethargy and anorexia are non‑specific — needs exam")
        add_cond("Pain/stress", "Environmental or painful conditions reduce appetite and activity")
        add_cond("Infection", "Systemic or respiratory infections can present with these signs")
        reds = [
            "Breathing difficulty or collapse",
            "Continuous vomiting/diarrhea or blood",
            "Severe pain or seizures",
        ]
        care = [
            "Quiet, warm environment; easy access to water",
            "Avoid new foods/treats; monitor intake and output",
            "Vet visit if symptoms persist or any red flag",
        ]

    return {"conditions": conds, "red_flags": reds, "care": care}


def _update_entry(collection, item_id, data):
    for item in collection:
        if item.get("id") == item_id:
            item.update(data)
            save_data()
            return item
    return None

def _delete_entry(collection, item_id):
    for item in list(collection):
        if item.get("id") == item_id:
            collection.remove(item)
            save_data()
            return True
    return False


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
    updated = _update_entry(users, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/owner/delete")
def delete_owner():
    data = request.json or {}
    if _delete_entry(users, data.get("id")):
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
    updated = _update_entry(pets, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/delete_pet")
def delete_pet():
    data = request.json or {}
    if _delete_entry(pets, data.get("id")):
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
    updated = _update_entry(medical_history, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/medical/delete")
def delete_medical():
    data = request.json or {}
    if _delete_entry(medical_history, data.get("id")):
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
    updated = _update_entry(vaccines, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/vaccine/delete")
def delete_vaccine():
    data = request.json or {}
    if _delete_entry(vaccines, data.get("id")):
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
    updated = _update_entry(weights, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/weight/delete")
def delete_weight():
    data = request.json or {}
    if _delete_entry(weights, data.get("id")):
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
    updated = _update_entry(appointments, data.get("id"), data)
    if updated:
        return jsonify(updated)
    return jsonify({"error": "not found"}), 404


@app.post("/appointment/delete")
def delete_appointment():
    data = request.json or {}
    if _delete_entry(appointments, data.get("id")):
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


@app.post("/ai/diagnose_llm")
def ai_diagnose_llm():
    """Diagnosis-style answer using a veterinary QA LLM (FLAN-T5 base fine-tune).

    Returns a concise text answer. This is strictly educational — not medical advice.
    """
    body = request.json or {}
    symptoms = (body.get("symptoms") or "").strip()
    species = (body.get("species") or "").strip()
    age = body.get("age", None)
    mode = (body.get("mode") or "").strip().lower()  # 'llm_only' | ''
    fallback_enabled = os.environ.get("VET_QA_FALLBACK", "1") == "1"
    if mode == "llm_only":
        fallback_enabled = False

    if not symptoms:
        return jsonify({"error": "symptoms is required"}), 400

    pipe = get_vet_llm_pipeline()
    if pipe is None:
        return (
            jsonify(
                {
                    "error": "veterinary QA model not available",
                    "hint": "Install transformers+torch then restart: pip install transformers torch",
                }
            ),
            500,
        )

    parts = []
    if species:
        parts.append(species)
    if age is not None:
        parts.append(f"age {age}")
    parts.append(symptoms)
    ctx = ", ".join(parts)

    # Heuristic category to steer LLM
    def _triage_category(txt: str) -> str:
        t = (txt or "").lower()
        if any(k in t for k in ["bleed", "blood", "cut", "wound", "lacer", "nail", "claw", "paw", "pad", "limp", "non weight", "not pressing", "holding up"]):
            return "wound/trauma"
        if any(k in t for k in ["vomit", "diarr", "stool", "poop", "constipat", "nausea"]):
            return "gastrointestinal"
        if any(k in t for k in ["cough", "sneez", "wheeze", "breath", "nasal", "runny nose"]):
            return "respiratory"
        if any(k in t for k in ["itch", "rash", "skin", "flea", "hot spot", "wound"]):
            return "dermatologic"
        if any(k in t for k in ["seizure", "collapse", "stagger", "head tilt"]):
            return "neurologic"
        return "general"

    category = _triage_category(symptoms)

    # LLM-only mode: ask for clean bullet points and return plain answer
    if mode == "llm_only":
        # T5-friendly prompt
        bullet_prompt = (
            f"The likely medical causes for a {age} year old {species} with {symptoms} are:\n"
        )

        gen_kwargs = {
            "max_new_tokens": int(os.environ.get("VET_QA_MAX_TOKENS", 200)),
            "do_sample": True,
            "temperature": 0.8,
            "top_p": 0.95,
            "repetition_penalty": 1.2,
            "early_stopping": True,
        }

        try:
            out = pipe(bullet_prompt, **gen_kwargs)[0]["generated_text"].strip()

        except Exception as e:
            return jsonify({"error": f"generation failed: {e}"}), 500

        return jsonify({
            "answer": out,
            "source": "llm_fallback",
            "disclaimer": "Educational only — not a diagnosis. For urgent symptoms (breathing trouble, seizures, collapse, severe pain, continuous vomiting/diarrhea, blood), seek veterinary care immediately.",
            "model": os.environ.get("VET_QA_MODEL", "ahmed807762/flan-t5-base-veterinaryQA_data-v2"),
        })

    # Ask for strict JSON to avoid instruction echo and repetition
    prompt = (
        "You are a veterinary assistant. Analyze the case and reply with JSON ONLY.\n"
        f"Case -> species: {species or 'Unknown'}, age: {age if age is not None else 'Unknown'}, symptoms: {symptoms}.\n"
        f"Category hint: {category}. Prioritize guidance for this category.\n"
        "Return a JSON object with exactly these keys: \n"
        "{\n"
        "  \"conditions\": [ { \"name\": string, \"reason\": string }, { ... }, { ... } ],\n"
        "  \"red_flags\": [ string, ... ],\n"
        "  \"care\": [ string, ... ]\n"
        "}\n"
        "Constraints:\n"
        "- Keep reasons specific to the species when possible.\n"
        "- Educational tone; no medication dosages.\n"
        "- No extra text, headers, or explanations — JSON ONLY.\n"
    )

    try:
        import json as _json

        # Decoding tuned for structured JSON output
        sampling = os.environ.get("VET_QA_SAMPLING", "0") == "1"
        gen_kwargs = {
            "max_new_tokens": int(os.environ.get("VET_QA_MAX_TOKENS", 220)),
            "no_repeat_ngram_size": int(os.environ.get("VET_QA_NGRAM", 5)),
            "repetition_penalty": float(os.environ.get("VET_QA_REP", 1.2)),
            "early_stopping": True,
        }
        if sampling:
            gen_kwargs.update({
                "do_sample": True,
                "temperature": float(os.environ.get("VET_QA_TEMP", 0.5)),
                "top_p": float(os.environ.get("VET_QA_TOP_P", 0.9)),
                "top_k": int(os.environ.get("VET_QA_TOP_K", 50)),
            })
        else:
            gen_kwargs.update({
                "do_sample": False,
                "num_beams": int(os.environ.get("VET_QA_BEAMS", 4)),
                "length_penalty": float(os.environ.get("VET_QA_LEN_PEN", 1.0)),
            })

        raw = pipe(prompt, **gen_kwargs)[0]["generated_text"].strip()
        
        def _try_parse(s: str):
            try:
                return _json.loads(s)
            except Exception:
                import re as _re
                m = _re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return _json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        js = _try_parse(raw)
        if js is None:
            # Fallback: attempt a lighter prompt without schema
            alt_prompt = (
                "Vet assistant concise JSON. Case: "
                f"{ctx}. Keys: conditions(3x{{name,reason}}), red_flags[], care[]."
            )
            raw = pipe(alt_prompt, **gen_kwargs)[0]["generated_text"].strip()
            js = _try_parse(raw)
        source = "llm"
        if js is None and fallback_enabled:
            # Last resort: use rule-based fallback, include raw for debugging
            fb = _fallback_suggestions(species, age, symptoms)
            js = {**fb, "raw": raw}
            source = "fallback"
        elif js is None:
            js = {"conditions": [], "red_flags": [], "care": [], "raw": raw}
            source = "llm"
    except Exception as e:
        return jsonify({"error": f"generation failed: {e}"}), 500

    # Normalize result lengths and types
    def _to_str(x):
        return str(x).strip()

    conds = js.get("conditions") or []
    norm_conds = []
    for c in conds[:3]:
        if isinstance(c, dict):
            name = _to_str(c.get("name", "")).strip("- ")
            reason = _to_str(c.get("reason", ""))
            if name:
                norm_conds.append({"name": name, "reason": reason})
        elif isinstance(c, str) and c.strip():
            norm_conds.append({"name": c.strip(), "reason": ""})

    red_flags = [ _to_str(x) for x in (js.get("red_flags") or []) if _to_str(x) ]
    care = [ _to_str(x) for x in (js.get("care") or []) if _to_str(x) ]

    # If everything is empty, optionally construct rule-based suggestions
    if not norm_conds and not red_flags and not care and fallback_enabled:
        fb = _fallback_suggestions(species, age, symptoms)
        norm_conds = fb.get("conditions", [])
        red_flags = fb.get("red_flags", [])
        care = fb.get("care", [])
        source = "fallback"

    return jsonify({
        "conditions": norm_conds,
        "red_flags": red_flags[:6],
        "care": care[:6],
        "source": source,
        "raw": js.get("raw", None),
        "disclaimer": "Educational only — not a diagnosis. For urgent symptoms (breathing trouble, seizures, collapse, severe pain, continuous vomiting/diarrhea, blood), seek veterinary care immediately.",
        "model": os.environ.get("VET_QA_MODEL", "ahmed807762/flan-t5-base-veterinaryQA_data-v2"),
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


@app.route("/api/ai/diagnose_llm", methods=["POST"])
def api_diagnose_llm():
    return ai_diagnose_llm()

if __name__ == "__main__":
    app.run(debug=True)
