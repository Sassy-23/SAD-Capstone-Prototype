# audit.py
# Central audit logging helper
# Step 8A: foundation for audit logs

from datetime import datetime
from db import get_db_conn


def log_action(username, action, note=""):
    """
    Writes a single audit log entry to the logs table.
    """
    conn = get_db_conn()
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
