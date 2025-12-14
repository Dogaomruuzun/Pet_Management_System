import os
import sqlite3
from typing import Dict, List, Any, Optional


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "petms.db")
SCHEMA_FILE = os.path.join(BASE_DIR, "schema.sql")


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Ensure FK is on for this connection
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: Optional[sqlite3.Connection] = None) -> None:
    close_after = False
    if conn is None:
        conn = connect()
        close_after = True
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    if close_after:
        conn.close()


def fetch_all(conn: Optional[sqlite3.Connection] = None) -> Dict[str, List[Dict[str, Any]]]:
    close_after = False
    if conn is None:
        conn = connect()
        close_after = True
    cur = conn.cursor()

    def rows(q: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in cur.execute(q).fetchall()]

    data = {
        "users": rows("SELECT id, name, email, password, role, phone, address FROM users"),
        "pets": rows("SELECT id, name, age, type, photo, ownerId FROM pets"),
        "medical_history": rows(
            "SELECT id, petId, date, diagnosis, treatment, notes, attachment FROM medical_history"
        ),
        "vaccines": rows(
            "SELECT id, petId, vaccineName, dateGiven, nextDue FROM vaccines"
        ),
        "weights": rows("SELECT id, petId, weight, date FROM weights"),
        "appointments": rows(
            "SELECT id, petId, date, time, reason, vetId FROM appointments"
        ),
    }

    if close_after:
        conn.close()
    return data


def replace_all(data: Dict[str, List[Dict[str, Any]]], conn: Optional[sqlite3.Connection] = None) -> None:
    close_after = False
    if conn is None:
        conn = connect()
        close_after = True

    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    # Clear child tables first, then parents
    for table in ["appointments", "weights", "vaccines", "medical_history", "pets", "users"]:
        cur.execute(f"DELETE FROM {table}")

    # Insert parents then children
    def ensure_keys(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
        safe: List[Dict[str, Any]] = []
        for r in rows:
            d = {}
            for k in keys:
                d[k] = r.get(k)
            safe.append(d)
        return safe
    users_rows = ensure_keys(
        data.get("users", []),
        ["id", "name", "email", "password", "role", "phone", "address"],
    )
    cur.executemany(
        "INSERT INTO users (id, name, email, password, role, phone, address) VALUES (:id, :name, :email, :password, :role, :phone, :address)",
        users_rows,
    )
    user_ids = {r.get("id") for r in users_rows}

    pets_rows = ensure_keys(
        data.get("pets", []),
        ["id", "name", "age", "type", "photo", "ownerId"],
    )
    for pr in pets_rows:
        oid = pr.get("ownerId")
        if not oid or oid not in user_ids:
            pr["ownerId"] = None
    cur.executemany(
        "INSERT INTO pets (id, name, age, type, photo, ownerId) VALUES (:id, :name, :age, :type, :photo, :ownerId)",
        pets_rows,
    )
    pet_ids = {r.get("id") for r in pets_rows}

    med_rows = ensure_keys(
        data.get("medical_history", []),
        ["id", "petId", "date", "diagnosis", "treatment", "notes", "attachment"],
    )
    med_rows = [r for r in med_rows if r.get("petId") in pet_ids]
    cur.executemany(
        "INSERT INTO medical_history (id, petId, date, diagnosis, treatment, notes, attachment) VALUES (:id, :petId, :date, :diagnosis, :treatment, :notes, :attachment)",
        med_rows,
    )

    vac_rows = ensure_keys(
        data.get("vaccines", []),
        ["id", "petId", "vaccineName", "dateGiven", "nextDue"],
    )
    vac_rows = [r for r in vac_rows if r.get("petId") in pet_ids]
    cur.executemany(
        "INSERT INTO vaccines (id, petId, vaccineName, dateGiven, nextDue) VALUES (:id, :petId, :vaccineName, :dateGiven, :nextDue)",
        vac_rows,
    )

    wt_rows = ensure_keys(
        data.get("weights", []),
        ["id", "petId", "weight", "date"],
    )
    wt_rows = [r for r in wt_rows if r.get("petId") in pet_ids]
    cur.executemany(
        "INSERT INTO weights (id, petId, weight, date) VALUES (:id, :petId, :weight, :date)",
        wt_rows,
    )

    appt_rows = ensure_keys(
        data.get("appointments", []),
        ["id", "petId", "date", "time", "reason", "vetId"],
    )
    appt_rows = [r for r in appt_rows if r.get("petId") in pet_ids]
    cur.executemany(
        "INSERT INTO appointments (id, petId, date, time, reason, vetId) VALUES (:id, :petId, :date, :time, :reason, :vetId)",
        appt_rows,
    )

    conn.commit()
    if close_after:
        conn.close()
