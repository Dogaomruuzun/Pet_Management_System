# Pet Management Pro (Vet Panel)

## Students
- **Doğa Ömrüuzun** – 210201027  
- **Melis Gedik** – 220201027  

---

## Project Description
Pet Management Pro is a web-based veterinary clinic management system developed as a course project.  
The system allows veterinarians to manage pets, owners, medical records, and appointments through a simple and user-friendly interface.

The project includes an **AI-assisted backend** that provides intelligent diagnostic suggestions and triage advice based on symptoms.

---

## Project Requirements Compliance

This project fully satisfies the course requirements:

1. Frontend is developed using **HTML, CSS, and JavaScript**
2. Backend is developed using **Flask (Python)**
3. An **AI model runs on the backend** (Transformer-based LLM)
4. The project is under **Git source control**
5. The project is stored and maintained on **GitHub**
6. GitHub repository URL can be shared during development

---

## Features

### Authentication
- Veterinarian registration and login
- Secure logout system

### Dashboard
- Summary statistics (KPIs)
- Pet type distribution visualization

### Pet Management
- Add, edit, and delete pets
- Photo upload and preview support

### Owner Management
- Manage owner information (name, phone, email, address)

### Medical Records
- Clinical history records with attachments
- Vaccination tracking with next due dates

### Appointments
- Schedule and list veterinary appointments

### Weight Tracking
- Record pet weight
- Visualize weight history with charts

---

## AI Assistant (Backend)

The backend integrates advanced AI capabilities for veterinary support:

- **AI Diagnostic Assistant**: Uses a fine-tuned **FLAN-T5 (Seq2Seq)** model (`ahmed807762/flan-t5-base-veterinaryQA_data-v2`) to generate educational diagnostic suggestions based on species, age, and symptoms.
- **Intelligent Triage**: Automatically categorizes cases (e.g., Trauma, Gastrointestinal, Respiratory) using keyword analysis.
- **Robust Fallback System**: Includes a rule-based fallback engine to provide safe suggestions even if the AI model is unavailable.

All AI processing is performed locally on the server using `transformers` and `torch`.

---

## Technologies Used

### Frontend
- HTML  
- CSS  
- JavaScript  
- Chart.js  

### Backend
- Python  
- Flask  
- SQLite  

### AI / Machine Learning
- Transformers (Hugging Face)
- PyTorch  
- SentencePiece
- NumPy  

### Tools
- Git  
- GitHub  

---

## Project Structure

project-root/
│
├── frontend/
│ ├── index.html
│ ├── style.css
│ └── script.js
│
├── backend/
│ ├── app.py
│ ├── db.py
│ ├── init_db.py
│ ├── requirements.txt
│ └── model/ (Cached model artifacts)
│
└── README.md

---

## How to Run the Project

### Frontend

Open `frontend/index.html` in a web browser.  
*(Ensure the backend is running for full functionality)*

### Backend

1. **Navigate to backend directory**
 - 'cd backend'
2. **Install Dependencies**
 - 'pip install -r requirements.txt'
3. **Initialize Database**
 - 'python init_db.py'
4. **Run Application**
 - 'python app.py'
