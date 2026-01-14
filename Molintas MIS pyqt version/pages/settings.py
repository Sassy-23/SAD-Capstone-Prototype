# pages/settings.py
# Settings module
# Handles system configuration values

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QFileDialog
)
from PyQt6.QtCore import Qt
from db import get_db_conn, DB_PATH
from audit import log_action
import shutil
import os
from datetime import datetime


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # =========================
        # Page title
        # =========================
        title = QLabel("System Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # =========================
        # Settings table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Setting", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)

        # =========================
        # Edit section
        # =========================
        edit_layout = QHBoxLayout()

        edit_layout.addWidget(QLabel("Value:"))
        self.value_input = QLineEdit()
        edit_layout.addWidget(self.value_input)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_setting)
        edit_layout.addWidget(save_btn)

        edit_layout.addStretch()
        main_layout.addLayout(edit_layout)

        self.table.itemSelectionChanged.connect(self.load_selected_value)

        self.load_settings()

        # =========================
        # Backup & Restore
        # =========================
        maintenance_layout = QHBoxLayout()

        backup_btn = QPushButton("Backup Database")
        backup_btn.clicked.connect(self.backup_database)
        maintenance_layout.addWidget(backup_btn)

        restore_btn = QPushButton("Restore Database")
        restore_btn.clicked.connect(self.restore_database)
        maintenance_layout.addWidget(restore_btn)

        maintenance_layout.addStretch()
        main_layout.addLayout(maintenance_layout)

    # -------------------------------------------------
    # Load settings from database
    # -------------------------------------------------
    def load_settings(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT key, value FROM settings ORDER BY key")
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, s in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(str(s["key"])))
            self.table.setItem(r, 1, QTableWidgetItem(str(s["value"])))

        self.table.resizeColumnsToContents()

    # -------------------------------------------------
    # Load selected value into input
    # -------------------------------------------------
    def load_selected_value(self):
        selected = self.table.selectedItems()
        if not selected:
            return

        self.value_input.setText(selected[1].text())

    # -------------------------------------------------
    # Save updated setting value (NUMERIC SAFE)
    # -------------------------------------------------
    def save_setting(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a setting to update.")
            return

        key = selected[0].text()

        try:
            value = float(self.value_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Value", "Value must be a number.")
            return

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE settings
            SET value = ?
            WHERE key = ?
        """, (value, key))

        conn.commit()
        conn.close()

        log_action("SYSTEM", "Updated setting", f"{key} = {value}")

        self.load_settings()

        QMessageBox.information(
            self,
            "Settings Updated",
            f"{key} updated successfully."
        )

    # -------------------------------------------------
    # Backup database
    # -------------------------------------------------
    def backup_database(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"molintas_backup_{timestamp}.db"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Database",
            default_name,
            "Database Files (*.db)"
        )

        if not file_path:
            return

        try:
            shutil.copy(DB_PATH, file_path)
            QMessageBox.information(
                self,
                "Backup Successful",
                f"Backup saved as:\n{os.path.basename(file_path)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    # -------------------------------------------------
    # Restore database
    # -------------------------------------------------
    def restore_database(self):
        reply = QMessageBox.question(
            self,
            "Restore Database",
            "Restoring will overwrite the current database.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Database",
            "",
            "Database Files (*.db)"
        )

        if not file_path:
            return

        try:
            shutil.copy(file_path, DB_PATH)
            QMessageBox.information(
                self,
                "Restore Successful",
                "Database restored successfully.\n\n"
                "Please restart the application."
            )
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", str(e))
