# pages/audit_logs.py
# Audit Logs Viewer (ADMIN ONLY)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QPushButton
)
from PyQt6.QtCore import Qt
from db import get_db_conn


class AuditLogsPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # =========================
        # Title
        # =========================
        title = QLabel("Audit Logs")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # =========================
        # Table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Date & Time",
            "Username",
            "Action",
            "Note"
        ])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

        # =========================
        # Refresh Button
        # =========================
        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.clicked.connect(self.load_logs)
        layout.addWidget(refresh_btn)

        self.load_logs()

    # -------------------------------------------------
    # Load logs from database
    # -------------------------------------------------
    def load_logs(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT datetime, username, action, note
            FROM logs
            ORDER BY datetime DESC
        """)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, log in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(log["datetime"]))
            self.table.setItem(r, 1, QTableWidgetItem(log["username"]))
            self.table.setItem(r, 2, QTableWidgetItem(log["action"]))
            self.table.setItem(r, 3, QTableWidgetItem(log["note"] or ""))
