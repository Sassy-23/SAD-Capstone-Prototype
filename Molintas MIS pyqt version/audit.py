# audit.py
# Central audit logging helper

import sqlite3
from datetime import datetime
from db import DB_PATH


def log_action(username, action, note=None):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO logs (username, action, note, datetime)
            VALUES (?, ?, ?, ?)
        """, (
            username,
            action,
            note,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        conn.close()

    except sqlite3.OperationalError as e:
        print("AUDIT LOG FAILED:", e)
