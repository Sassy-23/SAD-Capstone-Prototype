# pages/users.py
# User Management module
# Matches current database schema

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from db import get_db_conn
import hashlib
from audit import log_action



class UsersPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # =========================
        # Page title
        # =========================
        title = QLabel("User Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # =========================
        # Users table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            "Username", "Role"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)

        # =========================
        # Add user section
        # =========================
        form_layout = QHBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        form_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addWidget(self.password_input)

        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "staff"])
        form_layout.addWidget(self.role_combo)

        add_btn = QPushButton("Add User")
        add_btn.clicked.connect(self.add_user)
        form_layout.addWidget(add_btn)

        main_layout.addLayout(form_layout)

        # =========================
        # Reset password button
        # =========================
        action_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset Password")
        reset_btn.clicked.connect(self.reset_password)


        action_layout.addWidget(reset_btn)
        action_layout.addStretch()
        main_layout.addLayout(action_layout)

        self.load_users()

    # -------------------------------------------------
    # Load users from database
    # -------------------------------------------------
    def load_users(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT username, role
            FROM users
            ORDER BY username
        """)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, u in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(u["username"]))
            self.table.setItem(r, 1, QTableWidgetItem(u["role"]))

    # -------------------------------------------------
    # Add new user
    # -------------------------------------------------
    def add_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        role = self.role_combo.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Invalid Input", "Username and password required.")
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (username, password_hash, role)
                VALUES (?, ?, ?)
            """, (username, password_hash, role))
            conn.commit()
        except Exception:
            QMessageBox.warning(self, "Error", "Username already exists.")
            conn.close()
            return

        conn.close()

        # ✅ LOG AFTER SUCCESSFUL ADD
        log_action("SYSTEM", "Added user", username)

        self.username_input.clear()
        self.password_input.clear()
        self.load_users()

        QMessageBox.information(self, "User Added", "User added successfully.")


    # -------------------------------------------------
    # Reset password to default
    # -------------------------------------------------
    def reset_password(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a user first.")
            return

        username = selected[0].text()
        default_password = "1234"
        password_hash = hashlib.sha256(default_password.encode()).hexdigest()

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE username = ?
        """, (password_hash, username))

        conn.commit()
        conn.close()

        # ✅ LOG AFTER SUCCESSFUL RESET
        log_action("SYSTEM", "Reset user password", username)

        QMessageBox.information(
            self,
            "Password Reset",
            "Password reset to default: 1234"
        )
