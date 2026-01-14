# pages/clients.py
# Client Management page
# Handles viewing, adding, editing, and deleting clients

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QDialog,
    QLineEdit, QComboBox, QFormLayout, QTabWidget
)
from PyQt6.QtCore import Qt
from db import get_db_conn
from audit import log_action


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

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_clients)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(toggle_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(refresh_btn)

        main_layout.addLayout(btn_layout)

        # =========================
        # Tabs
        # =========================
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Residential / Apartment
        self.res_table = QTableWidget()
        self.setup_table(self.res_table)
        self.tabs.addTab(self.res_table, "Household / Apartment")

        # Trucks
        self.truck_table = QTableWidget()
        self.setup_table(self.truck_table)
        self.tabs.addTab(self.truck_table, "Trucks")

        self.load_clients()

    # =========================
    # Table setup
    # =========================
    def setup_table(self, table):
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Name",
            "Type",
            "Billing Type",
            "Usage (m³)",
            "Bill (₱)",
            "Lifecycle",
            "Payment"
        ])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

    # =========================
    # Load clients
    # =========================
    def load_clients(self):
        conn = get_db_conn()
        cur = conn.cursor()

        # Residential + Apartment
        cur.execute("""
            SELECT * FROM clients
            WHERE type IN ('household', 'apartment')
            ORDER BY name
        """)
        res_rows = cur.fetchall()

        self.res_table.setRowCount(len(res_rows))
        for r, c in enumerate(res_rows):
            self.populate_row(self.res_table, r, c)

        # Trucks
        cur.execute("""
            SELECT * FROM clients
            WHERE type = 'truck'
            ORDER BY name
        """)
        truck_rows = cur.fetchall()

        self.truck_table.setRowCount(len(truck_rows))
        for r, c in enumerate(truck_rows):
            self.populate_row(self.truck_table, r, c)

        conn.close()

    def populate_row(self, table, row, c):
        table.setItem(row, 0, QTableWidgetItem(c["name"]))
        table.setItem(row, 1, QTableWidgetItem(c["type"]))
        table.setItem(row, 2, QTableWidgetItem(c["billing_type"] or "N/A"))
        table.setItem(row, 3, QTableWidgetItem(str(c["usage"])))
        table.setItem(row, 4, QTableWidgetItem(f"₱{c['bill']:.2f}"))

        # Lifecycle (Active / Inactive)
        table.setItem(row, 5, QTableWidgetItem(c["status"]))

        # Payment status — ONLY for non-trucks
        if c["type"] == "truck":
            table.setItem(row, 6, QTableWidgetItem("N/A"))
        else:
            table.setItem(row, 6, QTableWidgetItem(c["payment_status"]))


    # =========================
    # Helpers
    # =========================
    def get_active_table(self):
        return self.res_table if self.tabs.currentIndex() == 0 else self.truck_table

    def get_selected_row(self, table):
        selected = table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Select Client", "Please select a client first.")
            return None
        return selected[0].row()

    # =========================
    # Add client
    # =========================
    def add_client(self):
        dialog = ClientDialog(self)
        if dialog.exec():
            data = dialog.get_data()

            billing_type = None if data["type"] == "truck" else data["billing_type"]

            conn = get_db_conn()
            cur = conn.cursor()

            try:
                cur.execute("""
                    INSERT INTO clients
                    (name, type, usage, bill, date, status, payment_status, address, contact, billing_type)
                    VALUES (?, ?, 0, 0, NULL, 'Active', 'Unpaid', ?, ?, ?)
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

    # =========================
    # Edit client
    # =========================
    def edit_client(self):
        table = self.get_active_table()
        row = self.get_selected_row(table)
        if row is None:
            return

        name = table.item(row, 0).text()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients WHERE name = ?", (name,))
        client = cur.fetchone()
        conn.close()

        dialog = ClientDialog(self, client)
        if dialog.exec():
            data = dialog.get_data()
            billing_type = None if data["type"] == "truck" else data["billing_type"]

            conn = get_db_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE clients
                SET type=?, billing_type=?, address=?, contact=?
                WHERE name=?
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

    # =========================
    # Delete client
    # =========================
    def delete_client(self):
        table = self.get_active_table()
        row = self.get_selected_row(table)
        if row is None:
            return

        name = table.item(row, 0).text()

        if QMessageBox.question(self, "Confirm", f"Delete '{name}'?") != QMessageBox.StandardButton.Yes:
            return

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM clients WHERE name=?", (name,))
        cur.execute("DELETE FROM payments WHERE client=?", (name,))
        conn.commit()
        conn.close()

        log_action("SYSTEM", "Deleted client", name)
        self.load_clients()

    # =========================
    # Toggle status
    # =========================
    def toggle_status(self):
        table = self.get_active_table()
        row = self.get_selected_row(table)
        if row is None:
            return

        name = table.item(row, 0).text()
        current = table.item(row, 5).text()
        new = "Inactive" if current == "Active" else "Active"

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("UPDATE clients SET status=? WHERE name=?", (new, name))
        conn.commit()
        conn.close()

        log_action("SYSTEM", "Changed client status", f"{name}: {current} → {new}")
        self.load_clients()


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

        btns = QHBoxLayout()
        ok = QPushButton("Save")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)

        layout.addRow(btns)

    def on_type_changed(self):
        is_truck = self.type_input.currentText() == "truck"
        self.billing_input.setEnabled(not is_truck)
        if is_truck:
            self.billing_input.setCurrentIndex(-1)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "type": self.type_input.currentText(),
            "billing_type": self.billing_input.currentText(),
            "address": self.address_input.text().strip(),
            "contact": self.contact_input.text().strip()
        }
