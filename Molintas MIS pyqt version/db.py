# db.py
# Handles all database-related functions

import hashlib

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "molintas_full.db"

def get_db_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row

    # Allow SQLite to wait if database is busy
    conn.execute("PRAGMA busy_timeout = 5000;")

    return conn

def hash_password(password):
    # Same hashing logic as your Tkinter app
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_login(username, password):
    """
    Checks username and password against the database.
    Returns: (True, role) or (False, None)
    """
    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT password_hash, role FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return False, None

    if row["password_hash"] == hash_password(password):
        return True, row["role"]

    return False, None
