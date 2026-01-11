# pages/clients.py
# Client Management page
# Handles viewing, adding, editing, and deleting clients

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QDialog,
    QLineEdit, QComboBox, QFormLayout
)
from PyQt6.QtCore import Qt
from db import get_db_conn
from audit import log_action
from PyQt6.QtWidgets import QTabWidget



class ClientsPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # =========================
        # Page title
        # =========================
        title = QLabel("Client Management")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # =========================
        # Buttons
        # =========================
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Add Client")
        add_btn.clicked.connect(self.add_client)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(self.edit_client)

        del_btn = QPushButton("Delete Selected")
        del_btn.clicked.connect(self.delete_client)

        toggle_btn = QPushButton("Toggle Active / Inactive")
        toggle_btn.clicked.connect(self.toggle_status)
        btn_layout.addWidget(toggle_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_clients)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)

        main_layout.addLayout(btn_layout)

        # =========================
        # Client table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Type",
            "Billing Type",
            "Usage (m³)",
            "Bill (₱)",
            "Lifecycle",
            "Payment"
        ])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        main_layout.addWidget(self.table)

        self.load_clients()
        
    def refresh(self):
        self.load_clients()


    # -------------------------------------------------
    # Load all clients
    # -------------------------------------------------
    def load_clients(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM clients ORDER BY name")
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, c in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(r, 1, QTableWidgetItem(c["type"]))

            billing_display = c["billing_type"] if c["billing_type"] else "N/A"
            self.table.setItem(r, 2, QTableWidgetItem(billing_display))

            self.table.setItem(r, 3, QTableWidgetItem(str(c["usage"])))
            self.table.setItem(r, 4, QTableWidgetItem(f"₱{c['bill']:.2f}"))
            self.table.setItem(r, 5, QTableWidgetItem(c["status"]))
            self.table.setItem(r, 6, QTableWidgetItem(c["payment_status"]))


    # -------------------------------------------------
    # Add client
    # -------------------------------------------------
    def add_client(self):
        dialog = ClientDialog(self)
        if dialog.exec():
            data = dialog.get_data()

            billing_type = data["billing_type"]
            if data["type"].lower() == "truck":
                billing_type = None

            conn = get_db_conn()
            cur = conn.cursor()

            try:
                cur.execute("""
                    INSERT INTO clients
                    (name, type, usage, bill, date, status, address, contact, billing_type)
                    VALUES (?, ?, 0, 0, NULL, 'Unpaid', ?, ?, ?)
                """, (
                    data["name"],
                    data["type"],
                    data["address"],
                    data["contact"],
                    billing_type
                ))
                conn.commit()

                log_action("SYSTEM", "Added client", data["name"])

            except Exception:
                QMessageBox.critical(self, "Error", "Client name already exists.")
            finally:
                conn.close()

            self.load_clients()

    # -------------------------------------------------
    # Edit client
    # -------------------------------------------------
    def edit_client(self):
        row = self.get_selected_row()
        if row is None:
            return

        name = self.table.item(row, 0).text()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients WHERE name = ?", (name,))
        client = cur.fetchone()
        conn.close()

        if not client:
            return

        dialog = ClientDialog(self, client)
        if dialog.exec():
            data = dialog.get_data()

            billing_type = data["billing_type"]
            if data["type"].lower() == "truck":
                billing_type = None

            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE clients
                SET type = ?, billing_type = ?, address = ?, contact = ?
                WHERE name = ?
            """, (
                data["type"],
                billing_type,
                data["address"],
                data["contact"],
                name
            ))
            conn.commit()
            conn.close()

            log_action("SYSTEM", "Edited client", name)

            self.load_clients()

    # -------------------------------------------------
    # Delete client
    # -------------------------------------------------
    def delete_client(self):
        row = self.get_selected_row()
        if row is None:
            return

        name = self.table.item(row, 0).text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete client '{name}'?"
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM clients WHERE name = ?", (name,))
        cur.execute("DELETE FROM payments WHERE client = ?", (name,))
        conn.commit()
        conn.close()

        log_action("SYSTEM", "Deleted client", name)

        self.load_clients()


    def toggle_status(self):
        row = self.get_selected_row()
        if row is None:
            return

        name = self.table.item(row, 0).text()
        current_status = self.table.item(row, 5).text()

        new_status = "Inactive" if current_status == "Active" else "Active"

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE clients
            SET status = ?
            WHERE name = ?
        """, (new_status, name))
        conn.commit()
        conn.close()

        log_action(
            "SYSTEM",
            "Changed client status",
            f"{name}: {current_status} → {new_status}"
        )

        self.load_clients()

    # -------------------------------------------------
    # Helper
    # -------------------------------------------------
    def get_selected_row(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Select Client", "Please select a client first.")
            return None
        return selected[0].row()


# =====================================================
# Client Dialog
# =====================================================
class ClientDialog(QDialog):
    def __init__(self, parent, client=None):
        super().__init__(parent)

        self.setWindowTitle("Add Client" if client is None else "Edit Client")

        layout = QFormLayout(self)

        self.name_input = QLineEdit()

        self.type_input = QComboBox()
        self.type_input.addItems(["apartment", "household", "truck"])

        self.billing_input = QComboBox()
        self.billing_input.addItems(["Residential", "Commercial"])

        self.address_input = QLineEdit()
        self.contact_input = QLineEdit()

        self.type_input.currentTextChanged.connect(self.on_type_changed)

        if client:
            self.name_input.setText(client["name"])
            self.name_input.setDisabled(True)

            self.type_input.setCurrentText(client["type"])
            if client["billing_type"]:
                self.billing_input.setCurrentText(client["billing_type"])

            self.address_input.setText(client["address"] or "")
            self.contact_input.setText(client["contact"] or "")

            self.on_type_changed()

        layout.addRow("Name:", self.name_input)
        layout.addRow("Type:", self.type_input)
        layout.addRow("Billing Type:", self.billing_input)
        layout.addRow("Address:", self.address_input)
        layout.addRow("Contact:", self.contact_input)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout.addRow(btn_layout)

    def on_type_changed(self):
        if self.type_input.currentText().lower() == "truck":
            self.billing_input.setCurrentIndex(-1)
            self.billing_input.setEnabled(False)
        else:
            self.billing_input.setEnabled(True)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "type": self.type_input.currentText().strip().lower(),
            "billing_type": self.billing_input.currentText(),
            "address": self.address_input.text().strip(),
            "contact": self.contact_input.text().strip()
        }
