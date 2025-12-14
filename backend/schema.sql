-- SQLite schema for Pet Management System
-- Creates tables if they do not exist.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT,
  password TEXT,
  role TEXT,
  phone TEXT,
  address TEXT
);

-- Email is not enforced unique because owner entries may share emails
DROP INDEX IF EXISTS idx_users_email;
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS pets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  age REAL,
  type TEXT,
  photo TEXT,
  ownerId TEXT,
  FOREIGN KEY (ownerId) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_pets_owner ON pets(ownerId);

CREATE TABLE IF NOT EXISTS medical_history (
  id TEXT PRIMARY KEY,
  petId TEXT NOT NULL,
  date TEXT,
  diagnosis TEXT,
  treatment TEXT,
  notes TEXT,
  attachment TEXT,
  FOREIGN KEY (petId) REFERENCES pets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_medical_pet ON medical_history(petId);

CREATE TABLE IF NOT EXISTS vaccines (
  id TEXT PRIMARY KEY,
  petId TEXT NOT NULL,
  vaccineName TEXT,
  dateGiven TEXT,
  nextDue TEXT,
  FOREIGN KEY (petId) REFERENCES pets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vaccines_pet ON vaccines(petId);

CREATE TABLE IF NOT EXISTS weights (
  id TEXT PRIMARY KEY,
  petId TEXT NOT NULL,
  weight REAL,
  date TEXT,
  FOREIGN KEY (petId) REFERENCES pets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_weights_pet ON weights(petId);

CREATE TABLE IF NOT EXISTS appointments (
  id TEXT PRIMARY KEY,
  petId TEXT NOT NULL,
  date TEXT,
  time TEXT,
  reason TEXT,
  vetId TEXT,
  FOREIGN KEY (petId) REFERENCES pets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_appointments_pet ON appointments(petId);
