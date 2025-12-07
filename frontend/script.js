let currentUser = null;
let weightChart = null;
let petsCache = [];
let editingPetId = null;

// ===================== NAVIGATION & UI =====================

// (openPage moved to bottom)

// ===================== DROPDOWNS & USERS =====================

let usersCache = [];

// (loadDropdowns moved to bottom)

function toggleDark() {
    document.body.classList.toggle("dark");
}

function showRegister() {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("registerForm").style.display = "block";
}

function showLogin() {
    document.getElementById("registerForm").style.display = "none";
    document.getElementById("loginForm").style.display = "block";
}

// ===================== AUTH =====================

function checkLogin() {
    const stored = localStorage.getItem("user");
    if (stored) {
        currentUser = JSON.parse(stored);
        document.getElementById("sidebar").style.display = "block";
        openPage("dashboard");
    } else {
        openPage("loginPage");
    }
}


function register() {
    const name = document.getElementById("regName").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;
    // Role is always 'vet' for public registration
    const role = "vet";

    if (!name || !email || !password) {
        alert("Please fill all fields");
        return;
    }

    fetch("http://127.0.0.1:5000/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, role })
    })
        .then(r => {
            if (!r.ok) return r.json().then(e => { throw e; });
            return r.json();
        })
        .then(res => {
            alert("Registration successful! Please login.");
            showLogin();
        })
        .catch(err => alert(err.error || "Registration failed"));
}

function login() {
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    if (!email || !password) {
        alert("Please enter email and password");
        return;
    }

    fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    })
        .then(r => r.json())
        .then(res => {
            if (res.status === "ok") {
                currentUser = res.user;
                localStorage.setItem("user", JSON.stringify(currentUser));
                document.getElementById("sidebar").style.display = "block";
                openPage("dashboard");
            } else {
                alert(res.message || "Login failed");
            }
        })
        .catch(err => alert("Connection error"));
}

function logout() {
    currentUser = null;
    localStorage.removeItem("user");
    document.getElementById("sidebar").style.display = "none";
    openPage("loginPage");
}

// ===================== OWNERS (New) =====================

function addOwner() {
    const id = document.getElementById("ownerId").value;
    const name = document.getElementById("ownerName").value;
    const phone = document.getElementById("ownerPhone").value;
    const address = document.getElementById("ownerAddress").value;
    const email = document.getElementById("ownerEmail").value;

    if (!id || !name) {
        alert("ID (TC Number) and Name are required!");
        return;
    }

    fetch("http://127.0.0.1:5000/owner/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, name, phone, address, email })
    })
        .then(r => r.json())
        .then(() => {
            loadOwners();
            document.getElementById("ownerId").value = "";
            document.getElementById("ownerName").value = "";
            document.getElementById("ownerPhone").value = "";
            document.getElementById("ownerAddress").value = "";
            document.getElementById("ownerEmail").value = "";
        });
}

function loadOwners() {
    fetch("http://127.0.0.1:5000/users")
        .then(r => r.json())
        .then(data => {
            const owners = data.filter(u => u.role === 'owner');
            const list = document.getElementById("ownerList");
            list.innerHTML = "";
            owners.forEach(o => {
                list.innerHTML += `
                <div class="card">
                    <h3>${o.name}</h3>
                    <p><strong>ID:</strong> ${o.id}</p>
                    <p>Phone: ${o.phone || 'N/A'}</p>
                    <p>Address: ${o.address || 'N/A'}</p>
                    <div class="pet-actions">
                        <button class="edit-btn" onclick="openEditRecordModal('owner', '${o.id}')">Edit</button>
                        <button class="delete-btn" onclick="deleteRecord('owner', '${o.id}')">Delete</button>
                    </div>
                </div>`;
            });
        });
}


// ===================== GENERIC EDIT/DELETE/SEARCH =====================

let currentEditType = null;
let currentEditId = null;

// Cache for search filtering
let medicalCache = [];
let vaccineCache = [];
let weightCache = [];
let appointmentCache = [];
// Helper: extract petId from a free-form value like "Name (ID: 123)"
function extractIdFromString(val) {
    if (!val) return null;
    const m = String(val).match(/\(\s*ID:\s*(.*?)\s*\)$/i);
    return m ? m[1] : null;
}

// Search Filter
function searchRecords(type, query) {
    const rawQuery = query || "";
    const qLower = rawQuery.toLowerCase();
    const qId = extractIdFromString(rawQuery);

    const doFilter = () => {
        // Determine an exact pet if possible (by ID or exact name match)
        let targetPetId = null;
        if (qId) {
            targetPetId = qId;
        } else if (qLower.trim().length > 0) {
            const exactPet = petsCache.find(p => (p.name || "").toLowerCase() === qLower.trim());
            if (exactPet) targetPetId = exactPet.id;
        }

        // Fallback matcher (broad includes) used only when no exact pet resolved
        const isMatchBroad = (item) => {
            const pet = petsCache.find(p => p.id === item.petId);
            const name = pet ? (pet.name || "").toLowerCase() : "";
            return qLower.trim().length === 0 ? true : name.includes(qLower);
        };

        // Exact matcher by targetPetId when resolved
        const isMatchExact = (item) => String(item.petId) === String(targetPetId);

        if (type === 'medical') {
            const list = targetPetId ? medicalCache.filter(isMatchExact) : medicalCache.filter(isMatchBroad);
            renderMedical(list);
        }
        if (type === 'vaccines') {
            const list = targetPetId ? vaccineCache.filter(isMatchExact) : vaccineCache.filter(isMatchBroad);
            renderVaccines(list);
        }
        if (type === 'weight') {
            const list = targetPetId ? weightCache.filter(isMatchExact) : weightCache.filter(isMatchBroad);
            renderWeight(list);
            if (targetPetId) {
                updateWeightChart(list, [targetPetId]);
            } else {
                // If no query, chart all; if broad query, chart matched set
                if (qLower.trim().length === 0) {
                    updateWeightChart(weightCache);
                } else {
                    const petIds = [...new Set(list.map(x => x.petId))];
                    updateWeightChart(list, petIds);
                }
            }
        }
        if (type === 'appointments') {
            const list = targetPetId ? appointmentCache.filter(isMatchExact) : appointmentCache.filter(isMatchBroad);
            renderAppointments(list);
        }
    };

    // Ensure pets are loaded first
    if (!petsCache || petsCache.length === 0) {
        ensurePets(() => searchRecords(type, rawQuery));
        return;
    }

    // Load specific data if cache empty
    if (type === 'medical' && !medicalCache.length) { loadMedical().then(doFilter); return; }
    if (type === 'vaccines' && !vaccineCache.length) { loadVaccines().then(doFilter); return; }
    if (type === 'weight' && !weightCache.length) { loadWeight().then(doFilter); return; }
    if (type === 'appointments' && !appointmentCache.length) { loadAppointments().then(doFilter); return; }

    // If cache exists, filter immediately
    doFilter();
}

function deleteRecord(type, id) {
    if (!confirm("Are you sure?")) return;

    // Map type to endpoint
    let endpoint = "";
    if (type === 'owner') endpoint = "/owner/delete";
    if (type === 'medical') endpoint = "/medical/delete";
    if (type === 'vaccine') endpoint = "/vaccine/delete";
    if (type === 'weight') endpoint = "/weight/delete";
    if (type === 'appointment') endpoint = "/appointment/delete";

    fetch(`http://127.0.0.1:5000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id })
    })
        .then(r => r.json())
        .then(() => {
            // Reload page data
            if (type === 'owner') loadOwners();
            if (type === 'medical') loadMedical();
            if (type === 'vaccine') loadVaccines();
            if (type === 'weight') loadWeight();
            if (type === 'appointment') loadAppointments();
        });
}

function openEditRecordModal(type, id) {
    currentEditType = type;
    currentEditId = id;

    const container = document.getElementById("recordModalContent");
    container.innerHTML = ""; // Clear previous

    // Find the data object
    let item = null;
    if (type === 'owner') {
        // Need to fetch from users logic or cache. simplified: fetch all users again or use usersCache from loadDropdowns
        // Let's assume usersCache is fresh enough or fetch fresh
        // For simplicity, we restart loadDropdowns() often so usersCache -> global?
        // reusing loadDropdowns logic:
        fetch("http://127.0.0.1:5000/users").then(r => r.json()).then(users => {
            item = users.find(u => u.id === id);
            if (item) {
                container.innerHTML = `
                    <label>Name</label><input id="eOpt1" value="${item.name}">
                    <label>Phone</label><input id="eOpt2" value="${item.phone || ''}">
                    <label>Address</label><input id="eOpt3" value="${item.address || ''}">
                 `;
                document.getElementById("recordModal").style.display = "flex";
            }
        });
        return;
    }

    if (type === 'medical') item = medicalCache.find(x => x.id === id);
    if (type === 'vaccine') item = vaccineCache.find(x => x.id === id);
    if (type === 'weight') item = weightCache.find(x => x.id === id);
    if (type === 'appointment') item = appointmentCache.find(x => x.id === id);

    if (!item) return;

    if (type === 'medical') {
        container.innerHTML = `
            <label>Diagnosis</label><input id="eOpt1" value="${item.diagnosis}">
            <label>Treatment</label><input id="eOpt2" value="${item.treatment}">
            <label>Notes</label><textarea id="eOpt3">${item.notes}</textarea>
            <label>Date</label><input type="date" id="eOpt4" value="${item.date}">
        `;
    } else if (type === 'vaccine') {
        container.innerHTML = `
            <label>Vaccine Name</label><input id="eOpt1" value="${item.vaccineName}">
            <label>Date Given</label><input type="date" id="eOpt2" value="${item.dateGiven}">
            <label>Next Due</label><input type="date" id="eOpt3" value="${item.nextDue}">
        `;
    } else if (type === 'weight') {
        container.innerHTML = `
            <label>Weight (kg)</label><input type="number" id="eOpt1" value="${item.weight}">
            <label>Date</label><input type="date" id="eOpt2" value="${item.date}">
        `;
    } else if (type === 'appointment') {
        container.innerHTML = `
            <label>Date</label><input type="date" id="eOpt1" value="${item.date}">
            <label>Time</label><input type="time" id="eOpt2" value="${item.time}">
            <label>Reason</label><input id="eOpt3" value="${item.reason}">
        `;
    }

    document.getElementById("recordModal").style.display = "flex";
}

function saveRecordEdit() {
    let endpoint = "";
    let body = { id: currentEditId };

    if (currentEditType === 'owner') {
        endpoint = "/owner/edit";
        body.name = document.getElementById("eOpt1").value;
        body.phone = document.getElementById("eOpt2").value;
        body.address = document.getElementById("eOpt3").value;
    } else if (currentEditType === 'medical') {
        endpoint = "/medical/edit";
        body.diagnosis = document.getElementById("eOpt1").value;
        body.treatment = document.getElementById("eOpt2").value;
        body.notes = document.getElementById("eOpt3").value;
        body.date = document.getElementById("eOpt4").value;
    } else if (currentEditType === 'vaccine') {
        endpoint = "/vaccine/edit";
        body.vaccineName = document.getElementById("eOpt1").value;
        body.dateGiven = document.getElementById("eOpt2").value;
        body.nextDue = document.getElementById("eOpt3").value;
    } else if (currentEditType === 'weight') {
        endpoint = "/weight/edit";
        body.weight = Number(document.getElementById("eOpt1").value);
        body.date = document.getElementById("eOpt2").value;
    } else if (currentEditType === 'appointment') {
        endpoint = "/appointment/edit";
        body.date = document.getElementById("eOpt1").value;
        body.time = document.getElementById("eOpt2").value;
        body.reason = document.getElementById("eOpt3").value;
    }

    fetch(`http://127.0.0.1:5000${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    })
        .then(r => r.json())
        .then(() => {
            closeModal('recordModal');
            if (currentEditType === 'owner') loadOwners();
            if (currentEditType === 'medical') loadMedical();
            if (currentEditType === 'vaccine') loadVaccines();
            if (currentEditType === 'weight') loadWeight();
            if (currentEditType === 'appointment') loadAppointments();
        });
}

function closeModal(id) {
    document.getElementById(id).style.display = "none";
}

/* ===================== DASHBOARD ===================== */

function updateDashboard() {
    // Pets count
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(data => {
            document.getElementById("dashPets").textContent = data.length;

            // Chart
            const types = {};
            data.forEach(p => types[p.type] = (types[p.type] || 0) + 1);
            const ctx = document.getElementById("chartPetTypes");
            const existingChart = Chart.getChart(ctx);
            if (existingChart) existingChart.destroy();
            new Chart(ctx, {
                type: "pie",
                data: {
                    labels: Object.keys(types),
                    datasets: [{
                        data: Object.values(types),
                        backgroundColor: ["#4cd137", "#0097e6", "#e84118", "#fbc531"]
                    }]
                }
            });

            // Now fetch other stats utilizing the pet IDs
            fetchStats(data);
        });
}

function fetchStats(pets) {
    let appointmentCount = 0;
    let vaccineCount = 0;
    const today = new Date();
    const nextMonth = new Date();
    nextMonth.setDate(today.getDate() + 30);

    const promises = pets.map(p => {
        const p1 = fetch(`http://127.0.0.1:5000/appointment/${p.id}`).then(r => r.json()).then(apps => {
            apps.forEach(a => {
                const d = new Date(a.date);
                if (d >= today) appointmentCount++;
            });
        });
        const p2 = fetch(`http://127.0.0.1:5000/vaccine/${p.id}`).then(r => r.json()).then(vacs => {
            vacs.forEach(v => {
                const d = new Date(v.nextDue);
                if (d >= today && d <= nextMonth) vaccineCount++;
            });
        });
        return Promise.all([p1, p2]);
    });

    Promise.all(promises).then(() => {
        document.getElementById("dashAppointments").textContent = appointmentCount;
        document.getElementById("dashVaccines").textContent = vaccineCount;
    });
}


/* ===================== HELPERS ===================== */

function populatePetDatalists(pets, users) {
    const getOwnerName = (id) => {
        const u = users.find(u => u.id === id);
        return u ? u.name : "Unknown Owner";
    };

    // Populate global pets datalists
    const dl = document.getElementById("allPetsList");
    const searchDl = document.getElementById("petSearchList");

    if (dl) {
        dl.innerHTML = pets.map(p => `<option value="${p.name} (ID: ${p.id})">${p.type} - Owner: ${getOwnerName(p.ownerId)}</option>`).join("");
    }
    if (searchDl) {
        searchDl.innerHTML = pets.map(p => `<option value="${p.name} (ID: ${p.id})">`).join("");
    }
}

function resolveIdFromInput(inputId) {
    const el = document.getElementById(inputId);
    if (!el) return null;
    const val = el.value;
    const match = val.match(/\(ID: (.*)\)$/);
    return match ? match[1] : val;
}


/* ===================== PETS ===================== */

// Initialize dropdowns and other initial data

function loadDropdowns() {
    fetch("http://127.0.0.1:5000/users").then(r => r.json()).then(users => {
        usersCache = users;

        // Populate Owners Datalist
        const ownerDl = document.getElementById("ownersList");
        if (ownerDl) {
            const owners = users.filter(u => u.role === 'owner');
            ownerDl.innerHTML = owners.map(o => `<option value="${o.name} (ID: ${o.id})">${o.phone || ''}</option>`).join("");
        }

        // Populate Vets Dropdown
        const sel = document.getElementById("aVet");
        if (sel) {
            sel.innerHTML = '<option value="">-- Select Vet --</option>';
            const vets = users.filter(u => u.role === 'vet');
            vets.forEach(v => {
                sel.innerHTML += `<option value="${v.id}">${v.name}</option>`;
            });
        }

        // Refresh Pet Datalists if pets are loaded (to ensure owner names resolve)
        if (petsCache && petsCache.length > 0) {
            populatePetDatalists(petsCache, usersCache);
        }
    });
}

// Ensure loadDropdowns is called when opening pages
function openPage(pageId) {
    document.querySelectorAll(".page").forEach(p => {
        p.classList.remove("active");
        p.style.display = "none";
    });

    const target = document.getElementById(pageId);
    if (target) {
        target.classList.add("active");
        if (pageId === 'loginPage') {
            target.style.display = 'flex';
        } else {
            target.style.display = 'block';
        }
    }

    // Refresh data based on page
    loadDropdowns();

    if (pageId === 'dashboard') updateDashboard();
    if (pageId === 'pets') loadPets();
    if (pageId === 'owner') loadOwners();
    if (pageId === 'medical') loadMedical();
    if (pageId === 'vaccines') loadVaccines();
    if (pageId === 'weight') loadWeight();
    if (pageId === 'appointments') loadAppointments();
}

// File upload preview
const petPhotoFile = document.getElementById("petPhotoFile");
if (petPhotoFile) {
    petPhotoFile.addEventListener("change", function () {
        const file = this.files[0];
        if (file) {
            const formData = new FormData();
            formData.append("file", file);

            fetch("http://127.0.0.1:5000/upload", {
                method: "POST",
                body: formData
            })
                .then(r => r.json())
                .then(res => {
                    if (res.url) {
                        document.getElementById("petPhoto").value = res.url;
                        document.getElementById("petPhotoPreview").src = res.url;
                        document.getElementById("petPhotoPreview").style.display = "block";
                    }
                })
                .catch(err => alert("Upload failed"));
        }
    });
}

function clearPetForm() {
    document.getElementById("petName").value = "";
    document.getElementById("petAge").value = "";
    document.getElementById("petType").value = "";
    document.getElementById("petOwner").value = "";
    document.getElementById("petPhoto").value = "";
    document.getElementById("petPhotoFile").value = "";
    document.getElementById("petPhotoPreview").style.display = "none";
}

function addPet() {
    const photoUrl = document.getElementById("petPhoto").value;
    const ownerId = resolveIdFromInput("petOwnerName");

    if (!ownerId) { alert("Please select an owner"); return; }

    const data = {
        name: document.getElementById("petName").value,
        age: Number(document.getElementById("petAge").value),
        type: document.getElementById("petType").value,
        ownerId: ownerId,
        photo: photoUrl || "https://via.placeholder.com/150"
    };

    fetch("http://127.0.0.1:5000/add_pet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(r => r.json())
        .then(() => {
            loadPets();
            clearPetForm();
            // Stay on page or refresh list
        });
}

function loadPets() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(data => {
            petsCache = data;
            const list = document.getElementById("petList");
            list.innerHTML = "";
            data.forEach(p => {
                list.innerHTML += `
                <div class="pet-card">
                    <img src="${p.photo}" onerror="this.src='https://via.placeholder.com/150'" onclick="openPetDetail('${p.id}')">
                    <h3 onclick="openPetDetail('${p.id}')">${p.name}</h3>
                    <p>${p.type} — Age: ${p.age}</p>
                    <p>Owner: ${p.ownerId}</p>
                    <div class="pet-actions">
                       <button class="edit-btn" onclick="editPet('${p.id}', event)">Edit</button>
                       <button class="delete-btn" onclick="deletePet('${p.id}', event)">Delete</button>
                    </div>
                </div>`;
            });
        });
}

function deletePet(id, event) {
    if (event) event.stopPropagation();

    if (!confirm("Are you sure you want to delete this pet?")) return;

    fetch("http://127.0.0.1:5000/delete_pet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
    })
        .then(r => r.json())
        .then(() => loadPets());
}


function editPet(id, event) {
    if (event) event.stopPropagation();

    const pet = petsCache.find(p => p.id === id);
    if (!pet) return;

    editingPetId = id;
    document.getElementById("editName").value = pet.name;
    document.getElementById("editAge").value = pet.age;
    document.getElementById("editType").value = pet.type;
    document.getElementById("editPhoto").value = pet.photo;

    document.getElementById("editModal").style.display = "flex";
}

function closeEditModal() {
    document.getElementById("editModal").style.display = "none";
}

function savePetEdit() {
    fetch("http://127.0.0.1:5000/edit_pet", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            id: editingPetId,
            name: document.getElementById("editName").value,
            age: Number(document.getElementById("editAge").value),
            type: document.getElementById("editType").value,
            photo: document.getElementById("editPhoto").value,
            ownerId: petsCache.find(p => p.id === editingPetId).ownerId
        })
    })
        .then(r => r.json())
        .then(() => {
            closeEditModal();
            loadPets();
        });
}

// ===================== MODULE RENDERERS =====================

function ensurePets(callback) {
    if (petsCache && petsCache.length > 0) {
        callback(petsCache);
    } else {
        fetch("http://127.0.0.1:5000/pets")
            .then(r => r.json())
            .then(data => {
                petsCache = data;
                callback(data);
            });
    }
}

function loadMedical() {
    return new Promise((resolve) => {
        ensurePets((pets) => {
            let promises = pets.map(p => fetch(`http://127.0.0.1:5000/medical/${p.id}`).then(r => r.json()));
            Promise.all(promises).then(results => {
                medicalCache = results.flat();
                renderMedical(medicalCache);
                resolve(medicalCache);
            });
        });
    });
}

function renderMedical(list) {
    const container = document.getElementById("medicalList");
    container.innerHTML = "";
    list.forEach(m => {
        const pet = petsCache.find(p => p.id === m.petId);
        const pName = pet ? pet.name : "Unknown";
        container.innerHTML += `
            <div class="record-item">
                <div>
                    <strong>${pName} (${m.date})</strong><br>
                    Diag: ${m.diagnosis}<br>
                    Treat: ${m.treatment}
                </div>
                <div class="record-actions">
                    <button class="edit-btn" onclick="openEditRecordModal('medical', '${m.id}')">Edit</button>
                    <button class="delete-btn" onclick="deleteRecord('medical', '${m.id}')">Del</button>
                </div>
            </div>`;
    });
}

function loadVaccines() {
    return new Promise((resolve) => {
        ensurePets((pets) => {
            let promises = pets.map(p => fetch(`http://127.0.0.1:5000/vaccine/${p.id}`).then(r => r.json()));
            Promise.all(promises).then(results => {
                vaccineCache = results.flat();
                renderVaccines(vaccineCache);
                resolve(vaccineCache);
            });
        });
    });
}

function renderVaccines(list) {
    const container = document.getElementById("vaccineList");
    container.innerHTML = "";
    list.forEach(v => {
        const pet = petsCache.find(p => p.id === v.petId);
        container.innerHTML += `
            <div class="record-item">
                <div>
                    <strong>${pet ? pet.name : '?'} - ${v.vaccineName}</strong><br>
                    Given: ${v.dateGiven} | Due: ${v.nextDue}
                </div>
                <div class="record-actions">
                    <button class="edit-btn" onclick="openEditRecordModal('vaccine', '${v.id}')">Edit</button>
                    <button class="delete-btn" onclick="deleteRecord('vaccine', '${v.id}')">Del</button>
                </div>
            </div>`;
    });
}

function loadWeight() {
    return new Promise((resolve) => {
        ensurePets((pets) => {
            let promises = pets.map(p => fetch(`http://127.0.0.1:5000/weight/${p.id}`).then(r => r.json()));
            Promise.all(promises).then(results => {
                weightCache = results.flat();
                renderWeight(weightCache);
                updateWeightChart(weightCache);
                resolve(weightCache);
            });
        });
    });
}

function renderWeight(list) {
    const container = document.getElementById("weightList");
    container.innerHTML = "";
    // sort by date desc make copy to not affect cache order?
    const sorted = [...list].sort((a, b) => new Date(b.date) - new Date(a.date));

    sorted.forEach(w => {
        const pet = petsCache.find(p => p.id === w.petId);
        container.innerHTML += `
            <div class="record-item">
                <div>
                    <strong>${pet ? pet.name : '?'}</strong>: ${w.weight}kg on ${w.date}
                </div>
                <div class="record-actions">
                    <button class="edit-btn" onclick="openEditRecordModal('weight', '${w.id}')">Edit</button>
                    <button class="delete-btn" onclick="deleteRecord('weight', '${w.id}')">Del</button>
                </div>
            </div>`;
    });
}

function loadAppointments() {
    return new Promise((resolve) => {
        ensurePets((pets) => {
            let promises = pets.map(p => fetch(`http://127.0.0.1:5000/appointment/${p.id}`).then(r => r.json()));
            Promise.all(promises).then(results => {
                appointmentCache = results.flat();
                renderAppointments(appointmentCache);
                resolve(appointmentCache);
            });
        });
    });
}

function renderAppointments(list) {
    const container = document.getElementById("appointmentList");
    container.innerHTML = "";
    list.forEach(a => {
        const pet = petsCache.find(p => p.id === a.petId);
        container.innerHTML += `
            <div class="record-item">
                <div>
                    <strong>${pet ? pet.name : '?'}</strong><br>
                    ${a.date} at ${a.time}<br>
                    ${a.reason}
                </div>
                <div class="record-actions">
                    <button class="edit-btn" onclick="openEditRecordModal('appointment', '${a.id}')">Edit</button>
                    <button class="delete-btn" onclick="deleteRecord('appointment', '${a.id}')">Del</button>
                </div>
            </div>`;
    });
}

// Chart Logic Updated
let weightChartInstance = null;

function updateWeightChart(data, filterPetIds = null) {
    const ctx = document.getElementById("weightChart").getContext("2d");

    // Group by pet
    // If filterPetIds is set, only use those
    const petsData = {};

    data.forEach(d => {
        if (filterPetIds && !filterPetIds.includes(d.petId)) return;

        if (!petsData[d.petId]) petsData[d.petId] = [];
        petsData[d.petId].push({ x: d.date, y: d.weight });
    });

    const datasets = Object.keys(petsData).map(petId => {
        const pet = petsCache.find(p => p.id === petId);
        // sort by date
        petsData[petId].sort((a, b) => new Date(a.x) - new Date(b.x));
        return {
            label: pet ? pet.name : "Unknown",
            data: petsData[petId].map(d => d.y),
            borderColor: getRandomColor(),
            fill: false
        };
    });

    // Simplification: Creating unique sorted labels (dates)
    const allDates = [...new Set(data.filter(d => !filterPetIds || filterPetIds.includes(d.petId)).map(d => d.date))].sort();

    // Re-map data to align with allDates (insert nulls if missing)
    const finalDatasets = datasets.map(ds => {
        const petId = Object.keys(petsData).find(key => {
            const pet = petsCache.find(p => p.id === key);
            return pet && pet.name === ds.label;
        });

        const mappedData = allDates.map(date => {
            const entry = petsData[petId].find(d => d.x === date);
            return entry ? entry.y : null;
        });

        return { ...ds, data: mappedData };
    });

    if (weightChartInstance) weightChartInstance.destroy();
    weightChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: allDates,
            datasets: finalDatasets
        },
        options: { responsive: true, preserveAspectRatio: false }
    });
}

function getRandomColor() {
    var letters = '0123456789ABCDEF';
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

/* ===================== MEDICAL HISTORY ===================== */

function addMedical() {
    const petId = resolveIdFromInput("medPetName");
    if (!petId) { alert("Select a pet"); return; }

    const data = {
        petId: petId,
        date: document.getElementById("medDate").value,
        diagnosis: document.getElementById("medDiag").value,
        treatment: document.getElementById("medTreat").value,
        notes: document.getElementById("medNotes").value,
        attachment: document.getElementById("medAttach").value
    };

    fetch("http://127.0.0.1:5000/medical/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(r => r.json())
        .then(() => {
            loadMedical();
            // Clear form
            document.getElementById("medDiag").value = "";
            document.getElementById("medTreat").value = "";
            document.getElementById("medNotes").value = "";
            document.getElementById("medAttach").value = "";
        });
}

/* ===================== VACCINES ===================== */

function addVaccine() {
    const petId = resolveIdFromInput("vacPetName");
    if (!petId) { alert("Select a pet"); return; }

    const data = {
        petId: petId,
        vaccineName: document.getElementById("vacName").value,
        dateGiven: document.getElementById("vacGiven").value,
        nextDue: document.getElementById("vacNext").value
    };

    fetch("http://127.0.0.1:5000/vaccine/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(r => r.json())
        .then(() => {
            loadVaccines();
            document.getElementById("vacName").value = "";
        });
}

/* ===================== WEIGHT TRACKING ===================== */

function addWeight() {
    const petId = resolveIdFromInput("wPetName");
    if (!petId) { alert("Select a pet"); return; }

    const data = {
        petId: petId,
        weight: Number(document.getElementById("wValue").value),
        date: document.getElementById("wDate").value
    };

    fetch("http://127.0.0.1:5000/weight/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(() => loadWeight());
}

// (Removed duplicate legacy loadWeight; using the cached version above)

/* ===================== APPOINTMENTS ===================== */

function addAppointment() {
    const petId = resolveIdFromInput("aPetName");
    if (!petId) { alert("Select a pet"); return; }

    const data = {
        petId: petId,
        date: document.getElementById("aDate").value,
        time: document.getElementById("aTime").value,
        reason: document.getElementById("aReason").value,
        vetId: document.getElementById("aVet").value
    };

    fetch("http://127.0.0.1:5000/appointment/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    })
        .then(() => loadAppointments());
}

// (Removed duplicate legacy loadAppointments; using the cached version above)

/* ===================== OWNER INFO ===================== */

function getOwnerPets() {
    const val = document.getElementById("ownerSearch").value;
    fetch(`http://127.0.0.1:5000/owner/${val}`)
        .then(r => r.json())
        .then(list => {
            const container = document.getElementById("ownerPets");
            container.innerHTML = "";
            list.forEach(p => {
                container.innerHTML += `
                <div class="pet-card">
                    <img src="${p.photo}" onerror="this.src='https://via.placeholder.com/150'">
                    <h3>${p.name}</h3>
                    <p>${p.type}</p>
                    <p>Age: ${p.age}</p>
                </div>`;
            });
        });
}

/* ===================== AI MODELS ===================== */

function aiLifespan() {
    fetch("http://127.0.0.1:5000/ai/lifespan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ age: Number(document.getElementById("aiAge").value) })
    })
        .then(r => r.json())
        .then(res => document.getElementById("aiLifeResult").textContent = res.prediction);
}

function aiHealth() {
    fetch("http://127.0.0.1:5000/ai/health_score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            age: Number(document.getElementById("aiHSAge").value),
            weight: Number(document.getElementById("aiHSWeight").value)
        })
    })
        .then(r => r.json())
        .then(res => document.getElementById("aiHealthResult").textContent = res.prediction);
}

function aiBreed() {
    fetch("http://127.0.0.1:5000/ai/breed_risk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            age: Number(document.getElementById("aiBreedAge").value)
        })
    })
        .then(r => r.json())
        .then(res => document.getElementById("aiBreedResult").textContent = res.prediction);
}

function openPetDetail(id) {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(all => {
            const pet = all.find(p => String(p.id).trim() === String(id).trim());
            const content = document.getElementById("petDetailContent");

            if (!pet) {
                content.innerHTML = "<h2>Pet Not Found</h2>";
                return;
            }

            content.innerHTML = `
                <div class="card">
                    <img src="${pet.photo}" style="width:200px; border-radius:10px; margin-bottom:15px;" onerror="this.src='https://via.placeholder.com/150'">
                    <h2>${pet.name}</h2>
                    <p><strong>Type:</strong> ${pet.type}</p>
                    <p><strong>Age:</strong> ${pet.age}</p>
                    <p><strong>Owner ID:</strong> ${pet.ownerId}</p>
                </div>

                <div class="card">
                    <h2>Medical History</h2>
                    <div id="detailMedical"></div>
                </div>

                <div class="card">
                    <h2>Vaccinations</h2>
                    <div id="detailVaccines"></div>
                </div>

                <div class="card">
                    <h2>Weight Tracking</h2>
                    <div id="detailWeight"></div>
                </div>

                <div class="card">
                    <h2>Appointments</h2>
                    <div id="detailAppointments"></div>
                </div>
            `;

            openPage("petDetail");
            loadPetDetailSections(pet.id);
        });
}

function loadPetDetailSections(id) {
    fetch(`http://127.0.0.1:5000/medical/${id}`).then(r => r.json()).then(list => {
        const div = document.getElementById("detailMedical");
        div.innerHTML = "";
        list.forEach(m => div.innerHTML += `<p>${m.date}: ${m.diagnosis}</p>`);
    });

    fetch(`http://127.0.0.1:5000/vaccine/${id}`).then(r => r.json()).then(list => {
        const div = document.getElementById("detailVaccines");
        div.innerHTML = "";
        list.forEach(v => div.innerHTML += `<p>${v.vaccineName} (${v.dateGiven})</p>`);
    });

    fetch(`http://127.0.0.1:5000/weight/${id}`).then(r => r.json()).then(list => {
        const div = document.getElementById("detailWeight");
        div.innerHTML = "";
        list.forEach(w => div.innerHTML += `<p>${w.date}: ${w.weight}kg</p>`);
    });

    fetch(`http://127.0.0.1:5000/appointment/${id}`).then(r => r.json()).then(list => {
        const div = document.getElementById("detailAppointments");
        div.innerHTML = "";
        list.forEach(a => div.innerHTML += `<p>${a.date}: ${a.reason}</p>`);
    });
}


/* ===================== INITIAL ===================== */

window.onload = () => {
    checkLogin();
};
