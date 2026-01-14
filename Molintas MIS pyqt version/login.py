# login.py
# Handles the login screen and database authentication

from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox
)
from PyQt6.QtCore import Qt

from dashboard import DashboardWindow
from db import check_login
from audit import log_action



class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Molintas Water Services MIS - Login")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Molintas Water Services MIS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(20)

        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        # Password input
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        layout.addSpacing(10)

        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.attempt_login)
        layout.addWidget(login_btn)

    # -------------------------------------------------
    # Login logic (connected to SQLite)
    # -------------------------------------------------
    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Login Failed", "Please enter username and password")
            return

        success, role = check_login(username, password)

        if success:
            self.open_dashboard(username, role)
            
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password")

    def open_dashboard(self, username, role):
        self.dashboard = DashboardWindow(username, role, self)
        self.dashboard.show()
        self.hide()
        log_action(username, "Logged in")
