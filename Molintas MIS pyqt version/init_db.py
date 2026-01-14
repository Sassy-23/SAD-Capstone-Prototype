# init_db.py
# FINAL DATABASE INITIALIZATION
# Matches the current Molintas MIS application

import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "molintas_full.db"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # =========================
    # USERS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # =========================
    # CLIENTS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        name TEXT PRIMARY KEY,
        type TEXT NOT NULL,                -- household | apartment | truck
        billing_type TEXT,                 -- Residential | Commercial | NULL for truck
        usage REAL DEFAULT 0,
        bill REAL DEFAULT 0,
        date TEXT,                         -- last billing date
        status TEXT DEFAULT 'Active',      -- Active | Inactive
        payment_status TEXT DEFAULT 'Unpaid',
        address TEXT,
        contact TEXT
    )
    """)

    # =========================
    # CLIENT PAYMENTS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY (client) REFERENCES clients(name)
    )
    """)

    # =========================
    # TRUCK SALOK LOGS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS truck_saloks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        truck TEXT NOT NULL,
        drums INTEGER NOT NULL,
        price REAL NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        FOREIGN KEY (truck) REFERENCES clients(name)
    )
    """)

    # =========================
    # TRUCK PAYMENTS (IRREGULAR)
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS truck_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        truck TEXT NOT NULL,
        amount REAL NOT NULL,
        date TEXT NOT NULL,
        note TEXT,
        FOREIGN KEY (truck) REFERENCES clients(name)
    )
    """)

    # =========================
    # SETTINGS (ONLY USED ONES)
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value REAL NOT NULL
    )
    """)

    # =========================
    # AUDIT LOGS
    # =========================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        note TEXT,
        datetime TEXT NOT NULL
    )
    """)

    # =========================
    # DEFAULT USERS
    # =========================
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), "admin")
        )
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            ("staff", hash_password("staff123"), "staff")
        )

    # =========================
    # DEFAULT SETTINGS (₱ PER m³)
    # =========================
    default_settings = {
        "RES_RATE": 37,          # household/apartment rate per cubic meter
        "COM_RATE": 50,          # commercial rate per cubic meter
        "PRICE_PER_DRUM": 7      # truck salok price
    }

    for key, value in default_settings.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()
    print("✅ Database rebuilt successfully.")


if __name__ == "__main__":
    init_db()
