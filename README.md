# Pet Management Pro (Vet Panel)
Doğa Ömrüuzun -210201027
Melis Gedik -220201027

A lightweight veterinary clinic panel for managing **pets**, **owners**, and **clinical records** with an **AI Assistant**.
The frontend is built with **HTML/CSS/JavaScript** and the backend is built with **Flask (Python)**. Data is persisted to a local **SQLite** database, and AI models run on the backend.

## Features

- **Authentication**: Register + login (veterinarian account) and logout. fileciteturn1file13L79-L87
- **Dashboard**: KPIs + Pet type distribution chart (Chart.js). fileciteturn1file4L13-L37
- **Pets**: Add/edit/delete pets, including **photo upload + preview**. fileciteturn1file14L5-L22
- **Medical History**: Add and search clinical records. fileciteturn1file14L24-L51
- **Vaccinations**: Add and track next-due dates. fileciteturn1file3L3-L21
- **Weight Tracking**: Add weights and visualize with a chart. fileciteturn1file3L43-L60
- **Appointments**: Schedule and list appointments per pet. fileciteturn1file3L80-L102
- **Owners**: Manage owner profiles (ID, name, phone, address, email). fileciteturn1file12L14-L29
- **AI Assistant**:
  - Lifespan prediction (regression)
  - Health score prediction (regression)
  - “Breed risk” category (classification)
  - Symptom triage classifier + optional **LLM symptom assistant**
  fileciteturn1file12L36-L75

## Tech Stack

### Frontend
- HTML + CSS + JavaScript
- Chart.js (dashboard + weight chart) fileciteturn1file13L7-L9

### Backend
- Flask + flask-cors (REST endpoints, static serving) fileciteturn1file3L3-L6
- SQLite (local file database)

### AI / ML
- scikit-learn + numpy (classical ML models)
- transformers + torch (optional LLM assistant) fileciteturn1file9L40-L45

Dependencies are listed in `requirements.txt`. fileciteturn0file2L1-L6

## Project Structure 

> Your Flask app expects a `frontend/` directory for the static UI (HTML/CSS/JS).

```
project-root/
  backend/              # Flask backend (app.py, db.py, init_db.py, train_models.py, requirements.txt)
  frontend/             # index.html, style.css, script.js
  backend/model/        # generated .pkl files (after training)
  backend/uploads/      # uploaded pet images
  backend/petms.db      # SQLite DB file (created after init)
```

## Setup & Run (Local)

### 1) Create virtual environment + install deps
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2) Train AI models (creates `backend/model/*.pkl`)
```bash
python train_models.py
```
This generates pickled models for lifespan, health score, breed risk, and symptom classification. fileciteturn1file5L36-L63

### 3) Initialize the database
```bash
python init_db.py
```
This initializes SQLite and optionally migrates existing `data.json` into the DB. fileciteturn1file2L16-L35

### 4) Run the Flask server
```bash
python app.py
```
By default it runs on `http://127.0.0.1:5000` (debug mode).  
Open the UI in your browser (either served from Flask root route or open `frontend/index.html` directly depending on your folder layout).

## Core API Endpoints (selected)

### Auth
- `POST /register`
- `POST /login`
- `POST /logout`

### Pets / Owners
- `GET /pets`
- `POST /add_pet`, `POST /edit_pet`, `POST /delete_pet`
- `POST /owner/add` (and edit/delete)

### Records
- `GET /medical/<pet_id>`, `POST /medical/add`
- `GET /vaccine/<pet_id>`, `POST /vaccine/add`
- `GET /weight/<pet_id>`, `POST /weight/add`
- `GET /appointment/<pet_id>`, `POST /appointment/add`

### AI
- `POST /ai/lifespan`
- `POST /ai/health_score`
- `POST /ai/breed_risk`
- `POST /ai/diagnose` (symptom classifier)
- `POST /ai/diagnose_llm` (optional LLM assistant)

> If models are not found, the AI endpoints instruct you to run `python train_models.py`. fileciteturn1file3L123-L127

## Data Persistence

SQLite is used as the primary store (`petms.db`) with a schema loaded from `schema.sql`. fileciteturn1file0L6-L17  
The backend also keeps a legacy `data.json` as a backup. fileciteturn1file7L27-L47

## Git & GitHub 

1. Initialize git and commit regularly:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```
2. Create a GitHub repo and push:
   ```bash
   git remote add origin <YOUR_GITHUB_REPO_URL>
   git branch -M main
   git push -u origin main
   ```
3. **Send your instructor the GitHub URL** when you begin development (as requested).

## Troubleshooting

- **AI endpoints return “model not loaded”** → run `python train_models.py` first. fileciteturn1file3L123-L127  
- **Database errors / empty data** → run `python init_db.py` to create tables. fileciteturn1file2L16-L20  
- **LLM endpoint fails** → ensure `transformers` + `torch` are installed (they are listed in requirements). fileciteturn1file9L40-L45  

## Demo Flow (suggested)

1. Register → Login fileciteturn1file13L79-L87  
2. Add owner → add pet (upload photo) fileciteturn1file14L5-L19  
3. Add medical record / vaccine / weight / appointment fileciteturn1file14L24-L51  
4. View dashboard charts fileciteturn1file4L13-L37  
5. Use AI Assistant (lifespan/health/risk + symptom suggestions) fileciteturn1file12L36-L75  
