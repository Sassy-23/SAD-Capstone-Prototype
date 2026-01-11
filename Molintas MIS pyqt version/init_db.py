# init_db.py
# This file creates the database and all required tables
# Run this ONCE before starting the application

import sqlite3
import hashlib
from datetime import datetime
from db import DB_PATH


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # =========================
    # USERS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # =========================
    # CLIENTS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            name TEXT PRIMARY KEY,
            type TEXT,
            usage REAL,
            bill REAL,
            date TEXT,
            status TEXT DEFAULT 'Active',
            payment_status TEXT DEFAULT 'Unpaid',
            address TEXT,
            contact TEXT,
            billing_type TEXT DEFAULT 'Residential'
        )
    """)

    # =========================
    # PAYMENTS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client TEXT,
            amount REAL,
            date TEXT,
            note TEXT
        )
    """)

    # =========================
    # TRUCK SALOK TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS truck_saloks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truck TEXT,
            drums INTEGER,
            price REAL,
            date TEXT,
            time TEXT
        )
    """)
        # =========================
    # TRUCK PAYMENTS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS truck_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truck TEXT,
            amount REAL,
            date TEXT,
            note TEXT
        )
    """)


    # =========================
    # SETTINGS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # =========================
    # LOGS TABLE
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            note TEXT,
            datetime TEXT
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
    # DEFAULT SETTINGS
    # =========================
    default_settings = {
        "RATE_APARTMENT": "50",
        "RATE_HOUSEHOLD": "30",
        "PRICE_PER_DRUM": "7",
        "BILL_DAY": "4",
        "RES_BASE": "150",
        "RES_THRESHOLD": "10",
        "RES_RATE": "35",
        "COM_BASE": "300",
        "COM_THRESHOLD": "10",
        "COM_RATE": "50"
    }

    for key, value in default_settings.items():
        cur.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )

    conn.commit()
    conn.close()

    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
