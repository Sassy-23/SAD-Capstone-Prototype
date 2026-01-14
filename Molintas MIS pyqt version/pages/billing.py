# pages/billing.py
# Client Billing page
# Handles residential and commercial billing only (trucks excluded)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QLineEdit, QPushButton, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt
from datetime import datetime
from db import get_db_conn
from audit import log_action


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        
        # =========================
        # Page title
        # =========================
        title = QLabel("Client Billing")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # =========================
        # Clients table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name",
            "Type",
            "Billing Type",
            "Usage (m³)",
            "Bill (₱)",
            "Status",
            "Payment Status"
        ])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.show_details)

        main_layout.addWidget(self.table)

        # =========================
        # Refresh section
        # =========================
        refresh_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh Clients")
        refresh_btn.clicked.connect(self.refresh_clients)

        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()

        main_layout.addLayout(refresh_layout)


        # =========================
        # Add usage section
        # =========================
        usage_layout = QHBoxLayout()

        usage_layout.addWidget(QLabel("Usage (m³):"))
        self.usage_input = QLineEdit()
        self.usage_input.setPlaceholderText("Enter usage")
        usage_layout.addWidget(self.usage_input)

        add_usage_btn = QPushButton("Add Usage")
        add_usage_btn.clicked.connect(self.add_usage)
        usage_layout.addWidget(add_usage_btn)

        usage_layout.addStretch()
        main_layout.addLayout(usage_layout)

        # =========================
        # Payment section
        # =========================
        payment_group = QGroupBox("Payments")
        payment_layout = QHBoxLayout(payment_group)

        payment_layout.addWidget(QLabel("Amount (₱):"))
        self.payment_input = QLineEdit()
        self.payment_input.setPlaceholderText("Enter payment")
        payment_layout.addWidget(self.payment_input)

        pay_btn = QPushButton("Record Payment")
        pay_btn.clicked.connect(self.record_payment)
        payment_layout.addWidget(pay_btn)

        payment_layout.addStretch()
        main_layout.addWidget(payment_group)

        # =========================
        # Client details
        # =========================
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        main_layout.addWidget(self.details)

        # =========================
        # Payment history
        # =========================
        self.history = QTextEdit()
        self.history.setReadOnly(True)
        self.history.setPlaceholderText("Payment history will appear here...")
        main_layout.addWidget(self.history)

        self.load_clients()
        
    def refresh(self):
        self.load_clients()
        self.details.clear()
        self.history.clear()


    # -------------------------------------------------
    # Load clients (NON-TRUCK ONLY)
    # -------------------------------------------------
    def load_clients(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM clients
            WHERE type IN ('household', 'apartment')
            AND status = 'Active'
            ORDER BY name


        """)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, c in enumerate(rows):
            self.table.setItem(r, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(r, 1, QTableWidgetItem(c["type"]))

            billing_display = c["billing_type"] or "N/A"
            self.table.setItem(r, 2, QTableWidgetItem(billing_display))

            self.table.setItem(r, 3, QTableWidgetItem(str(c["usage"])))
            self.table.setItem(r, 4, QTableWidgetItem(f"₱{c['bill']:.2f}"))
            self.table.setItem(r, 5, QTableWidgetItem(c["status"]))
            self.table.setItem(r, 6, QTableWidgetItem(c["payment_status"]))



    def refresh_clients(self):
        self.load_clients()
        self.details.clear()
        self.history.clear()


    # -------------------------------------------------
    # Show selected client details
    # -------------------------------------------------
    def show_details(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            self.details.clear()
            self.history.clear()
            return

        row = selected[0].row()
        name = self.table.item(row, 0).text()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM clients WHERE name = ?", (name,))
        c = cur.fetchone()
        conn.close()

        if not c:
            return

        self.details.setText(
            f"Name: {c['name']}\n"
            f"Type: {c['type']}\n"
            f"Billing Type: {c['billing_type'] or 'N/A'}\n"
            f"Usage: {c['usage']} m³\n"
            f"Bill: ₱{c['bill']:.2f}\n"
            f"Lifecycle Status: {c['status']}\n"
            f"Payment Status: {c['payment_status']}\n"
        )

        self.load_payment_history(name)

    # -------------------------------------------------
    # Add usage and compute bill
    # -------------------------------------------------
    def add_usage(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Select Client", "Please select a client first.")
            return

        try:
            usage = float(self.usage_input.text())
            if usage <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Enter a valid usage amount.")
            return

        row = selected[0].row()
        name = self.table.item(row, 0).text()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT type, usage, bill, billing_type
            FROM clients
            WHERE name = ?
        """, (name,))
        client = cur.fetchone()

        if not client or client["type"].lower() == "truck" or not client["billing_type"]:
            conn.close()
            QMessageBox.warning(
                self,
                "Invalid Client",
                "Truck clients are billed through Truck Salok."
            )
            return

        added_bill = self.compute_charge(client["billing_type"], usage)

        new_usage = client["usage"] + usage
        new_bill = client["bill"] + added_bill

        bill_date = datetime.now().strftime("%Y-%m-%d")

        cur.execute("""
            UPDATE clients
            SET usage = ?, bill = ?, date = ?, payment_status = 'Unpaid'
            WHERE name = ?
        """, (new_usage, new_bill, bill_date, name))

        conn.commit()
        conn.close()

        log_action(
            "SYSTEM",
            "Added usage",
            f"{name}: +{usage} m³ (₱{added_bill:.2f})"
        )

        self.usage_input.clear()
        self.load_clients()
        self.show_details()

        QMessageBox.information(
            self,
            "Usage Added",
            f"Added {usage} m³\nCharge: ₱{added_bill:.2f}"
        )

    # -------------------------------------------------
    # Record payment
    # -------------------------------------------------
    def record_payment(self):
        selected = self.table.selectionModel().selectedRows()
        if not selected:
            QMessageBox.warning(self, "Select Client", "Please select a client first.")
            return

        try:
            amount = float(self.payment_input.text())
            if amount <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Enter a valid payment amount.")
            return

        row = selected[0].row()
        name = self.table.item(row, 0).text()

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT bill FROM clients WHERE name = ?", (name,))
        client = cur.fetchone()

        if not client:
            conn.close()
            return

        if amount > client["bill"]:
            conn.close()
            QMessageBox.warning(
                self,
                "Invalid Payment",
                "Payment cannot exceed the current bill."
            )
            return

        cur.execute("""
            INSERT INTO payments (client, amount, date, note)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            amount,
            datetime.now().strftime("%Y-%m-%d"),
            "Payment received"
        ))

        new_bill = client["bill"] - amount
        payment_status = "Paid" if new_bill == 0 else "Unpaid"


        cur.execute("""
            UPDATE clients
            SET bill = ?, payment_status = ?
            WHERE name = ?
        """, (new_bill, payment_status, name))

        conn.commit()
        conn.close()

        log_action(
            "SYSTEM",
            "Recorded payment",
            f"{name}: ₱{amount:.2f}"
        )

        self.payment_input.clear()
        self.load_clients()
        self.show_details()

        QMessageBox.information(
            self,
            "Payment Recorded",
            f"Payment of ₱{amount:.2f} recorded."
        )

    # -------------------------------------------------
    # Load payment history
    # -------------------------------------------------
    def load_payment_history(self, client_name):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT amount, date, note
            FROM payments
            WHERE client = ?
            ORDER BY date DESC
        """, (client_name,))
        rows = cur.fetchall()
        conn.close()

        if not rows:
            self.history.setText("No payments recorded.")
            return

        text = ""
        for r in rows:
            text += f"{r['date']} - ₱{r['amount']:.2f} ({r['note']})\n"

        self.history.setText(text)

    # -------------------------------------------------
    # Compute billing charge
    # -------------------------------------------------
    def compute_charge(self, billing_type, usage):
        conn = get_db_conn()
        cur = conn.cursor()

        if billing_type == "Commercial":
            rate = float(self.get_setting(cur, "COM_RATE", 50))
        else:
            rate = float(self.get_setting(cur, "RES_RATE", 37))

        conn.close()
        return usage * rate



    def get_setting(self, cursor, key, default):
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default
