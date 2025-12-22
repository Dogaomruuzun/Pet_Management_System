# Pet Management Pro (Vet Panel)

## Students
- **Doğa Ömrüuzun** – 210201027  
- **Melis Gedik** – 220201027  

---

## Project Description
Pet Management Pro is a web-based veterinary clinic management system developed as a course project.  
The system allows veterinarians to manage pets, owners, medical records, and appointments through a simple and user-friendly interface.

The project includes an **AI-assisted backend** that provides predictive analytics related to pet health.

---

## Project Requirements Compliance

This project fully satisfies the course requirements:

1. Frontend is developed using **HTML, CSS, and JavaScript**
2. Backend is developed using **Flask (Python)**
3. An **AI model runs on the backend**
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
- Add and search clinical history records
- Vaccination tracking with next due dates

### Appointments
- Schedule and list veterinary appointments

### Weight Tracking
- Record pet weight
- Visualize weight history with charts

---

## AI Assistant (Backend)

The backend includes machine learning models that provide:

- **Lifespan prediction** (Regression)
- **Health score prediction** (Regression)
- **Breed risk classification** (Classification)

AI models are trained using Python libraries and executed on the server side.

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
- Scikit-learn  
- Pandas  
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
│ ├── train_models.py
│ └── requirements.txt
│
└── README.md

---

## How to Run the Project

### Frontend

Open index.html in a web browser.
### Backend

pip install -r requirements.txt
python init_db.py
python train_models.py
python app.py
