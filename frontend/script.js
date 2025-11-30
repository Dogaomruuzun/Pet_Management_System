let currentUser = null;
let weightChart = null;
let petsCache = [];     // ✔ EKLENDİ
let editingPetId = null; // ✔ EKLENDİ


function openPage(id) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById(id).classList.add("active");
}

function toggleDark() {
    document.body.classList.toggle("dark");
}

/* ===================== LOGIN ===================== */

function login() {
    const data = {
        email: loginEmail.value,
        password: loginPassword.value,
        role: loginRole.value
    };

    fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(res => {
        if (res.status === "ok") {
            currentUser = res.user;

            openPage("dashboard");
            updateDashboard();
            loadPets();        // ✔ Login sonrası pet listesi otomatik yüklensin
            loadMedical();
            loadVaccines();
            loadWeight();
            loadAppointments();
        }
    });
}

/* ===================== DASHBOARD ===================== */

function updateDashboard() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(data => {
            dashPets.textContent = data.length;

            const types = {};
            data.forEach(p => types[p.type] = (types[p.type] || 0) + 1);

            const ctx = document.getElementById("chartPetTypes");
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
        });

    dashAppointments.textContent = "—";
    dashVaccines.textContent = "—";
}

/* ===================== PETS ===================== */

function clearPetForm() {
    petName.value = "";
    petAge.value = "";
    petType.value = "";
    petOwner.value = "";
    petPhoto.value = "";
}

function addPet() {
    const data = {
        name: petName.value,
        age: Number(petAge.value),
        type: petType.value,
        ownerId: petOwner.value,
        photo: petPhoto.value
    };

    fetch("http://127.0.0.1:5000/add_pet", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(() => {
        loadPets();         // ✔ Listeyi güncelle
        clearPetForm();     // ✔ Formu temizle
        openPage("pets");   // ✔ Pets sayfasına dön
    });
}

function loadPets() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(data => {
            petsCache = data;   // ✔ GLOBAL OLARAK KAYDET
            petList.innerHTML = "";
            data.forEach(p => {
                petList.innerHTML += `
                <div class="pet-card">
                    <img src="${p.photo}" onclick="openPetDetail('${p.id}')">
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
    event.stopPropagation();

    if (!confirm("Are you sure you want to delete this pet?")) return;

    fetch("http://127.0.0.1:5000/delete_pet", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ id: id })
    })
    .then(r => r.json())
    .then(() => loadPets());
}


function editPet(id, event) {
    event.stopPropagation();

    const pet = petsCache.find(p => p.id === id);
    if (!pet) return;

    editingPetId = id;

    editName.value = pet.name;
    editAge.value = pet.age;
    editType.value = pet.type;
    editPhoto.value = pet.photo;

    document.getElementById("editModal").style.display = "flex";
}





function savePetEdit() {
    fetch("http://127.0.0.1:5000/edit_pet", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            id: editingPetId,
            name: editName.value,
            age: Number(editAge.value),
            type: editType.value,
            photo: editPhoto.value,
            ownerId: petsCache.find(p => p.id === editingPetId).ownerId
        })
    })
    .then(r => r.json())
    .then(() => {
        closeEditModal();
        loadPets();
    });
}

function closeEditModal() {
    document.getElementById("editModal").style.display = "none";
}


/* ===================== MEDICAL HISTORY ===================== */

function addMedical() {
    const data = {
        petId: medPetId.value,
        date: medDate.value,
        diagnosis: medDiag.value,
        treatment: medTreat.value,
        notes: medNotes.value,
        attachment: medAttach.value
    };

    fetch("http://127.0.0.1:5000/medical/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(() => loadMedical());
}

function loadMedical() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(allPets => {
            medicalList.innerHTML = "";
            allPets.forEach(p => {
                fetch(`http://127.0.0.1:5000/medical/${p.id}`)
                    .then(r => r.json())
                    .then(records => {
                        records.forEach(rec => {
                            medicalList.innerHTML += `
                            <div>
                                <h3>${p.name}</h3>
                                <p>${rec.date}</p>
                                <p>${rec.diagnosis}</p>
                                <p>${rec.treatment}</p>
                                <p>${rec.notes}</p>
                                <a href="${rec.attachment}" target="_blank">View Attachment</a>
                            </div>`;
                        });
                    });
            });
        });
}

/* ===================== VACCINES ===================== */

function addVaccine() {
    const data = {
        petId: vacPetId.value,
        vaccineName: vacName.value,
        dateGiven: vacGiven.value,
        nextDue: vacNext.value
    };

    fetch("http://127.0.0.1:5000/vaccine/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(() => loadVaccines());
}

function loadVaccines() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(allPets => {
            vaccineList.innerHTML = "";
            allPets.forEach(p => {
                fetch(`http://127.0.0.1:5000/vaccine/${p.id}`)
                    .then(r => r.json())
                    .then(records => {
                        records.forEach(rec => {
                            vaccineList.innerHTML += `
                            <div>
                                <h3>${p.name}</h3>
                                <p>${rec.vaccineName}</p>
                                <p>Given: ${rec.dateGiven}</p>
                                <p>Next: ${rec.nextDue}</p>
                            </div>`;
                        });
                    });
            });
        });
}

/* ===================== WEIGHT TRACKING ===================== */

function addWeight() {
    const data = {
        petId: wPetId.value,
        weight: Number(wValue.value),
        date: wDate.value
    };

    fetch("http://127.0.0.1:5000/weight/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(() => loadWeight());
}

function loadWeight() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(allPets => {
            weightList.innerHTML = "";

            if (weightChart) weightChart.destroy();

            allPets.forEach(p => {
                fetch(`http://127.0.0.1:5000/weight/${p.id}`)
                    .then(r => r.json())
                    .then(records => {
                        if (records.length > 0) {
                            const labels = records.map(r => r.date);
                            const values = records.map(r => r.weight);

                            const ctx = document.getElementById("weightChart");
                            weightChart = new Chart(ctx, {
                                type: "line",
                                data: {
                                    labels: labels,
                                    datasets: [{
                                        data: values,
                                        borderColor: "#4cd137",
                                        fill: false
                                    }]
                                }
                            });

                            records.forEach(rec => {
                                weightList.innerHTML += `
                                <div>
                                    <h3>${p.name}</h3>
                                    <p>${rec.date}</p>
                                    <p>${rec.weight} kg</p>
                                </div>`;
                            });
                        }
                    });
            });
        });
}

/* ===================== APPOINTMENTS ===================== */

function addAppointment() {
    const data = {
        petId: aPetId.value,
        date: aDate.value,
        time: aTime.value,
        reason: aReason.value,
        vetId: aVet.value
    };

    fetch("http://127.0.0.1:5000/appointment/add", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    })
    .then(() => loadAppointments());
}

function loadAppointments() {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(allPets => {
            appointmentList.innerHTML = "";
            allPets.forEach(p => {
                fetch(`http://127.0.0.1:5000/appointment/${p.id}`)
                    .then(r => r.json())
                    .then(records => {
                        records.forEach(rec => {
                            appointmentList.innerHTML += `
                            <div>
                                <h3>${p.name}</h3>
                                <p>${rec.date} ${rec.time}</p>
                                <p>${rec.reason}</p>
                            </div>`;
                        });
                    });
            });
        });
}

/* ===================== OWNER INFO ===================== */

function getOwnerPets() {
    fetch(`http://127.0.0.1:5000/owner/${ownerSearch.value}`)
        .then(r => r.json())
        .then(list => {
            ownerPets.innerHTML = "";
            list.forEach(p => {
                ownerPets.innerHTML += `
                <div class="pet-card">
                    <img src="${p.photo}">
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
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ age: Number(aiAge.value) })
    })
    .then(r => r.json())
    .then(res => aiLifeResult.textContent = res.prediction);
}

function aiHealth() {
    fetch("http://127.0.0.1:5000/ai/health_score", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            age: Number(aiHSAge.value),
            weight: Number(aiHSWeight.value)
        })
    })
    .then(r => r.json())
    .then(res => aiHealthResult.textContent = res.prediction);
}

function aiBreed() {
    fetch("http://127.0.0.1:5000/ai/breed_risk", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            age: Number(aiBreedAge.value)
        })
    })
    .then(r => r.json())
    .then(res => aiBreedResult.textContent = res.prediction);
}
function openPetDetail(id) {
    fetch("http://127.0.0.1:5000/pets")
        .then(r => r.json())
        .then(all => {

            const pet = all.find(p => String(p.id).trim() === String(id).trim());

            if (!pet) {
                petDetailContent.innerHTML = "<h2>Pet Not Found</h2>";
                return;
            }

            petDetailContent.innerHTML = `
                <div class="card">
                    <img src="${pet.photo}" style="width:200px; border-radius:10px; margin-bottom:15px;">
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

    fetch(`http://127.0.0.1:5000/medical/${id}`)
        .then(r => r.json())
        .then(list => {
            detailMedical.innerHTML = "";
            list.forEach(m => {
                detailMedical.innerHTML += `
                <div>
                    <p>${m.date}</p>
                    <p>${m.diagnosis}</p>
                    <p>${m.treatment}</p>
                    <p>${m.notes}</p>
                </div>`;
            });
        });

    fetch(`http://127.0.0.1:5000/vaccine/${id}`)
        .then(r => r.json())
        .then(list => {
            detailVaccines.innerHTML = "";
            list.forEach(v => {
                detailVaccines.innerHTML += `
                <div>
                    <p>${v.vaccineName}</p>
                    <p>Given: ${v.dateGiven}</p>
                    <p>Next: ${v.nextDue}</p>
                </div>`;
            });
        });

    fetch(`http://127.0.0.1:5000/weight/${id}`)
        .then(r => r.json())
        .then(list => {
            detailWeight.innerHTML = "";
            list.forEach(w => {
                detailWeight.innerHTML += `
                <div>
                    <p>${w.date}</p>
                    <p>${w.weight} kg</p>
                </div>`;
            });
        });

    fetch(`http://127.0.0.1:5000/appointment/${id}`)
        .then(r => r.json())
        .then(list => {
            detailAppointments.innerHTML = "";
            list.forEach(a => {
                detailAppointments.innerHTML += `
                <div>
                    <p>${a.date} ${a.time}</p>
                    <p>${a.reason}</p>
                </div>`;
            });
        });
}


/* ===================== INITIAL ===================== */

window.onload = () => {
    openPage("loginPage");
};
