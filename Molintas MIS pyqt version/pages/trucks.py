# pages/trucks.py
# Truck Salok module
# Handles truck water collection, payments, and balance computation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QMessageBox, QComboBox
)
from PyQt6.QtCore import Qt
from datetime import datetime
from db import get_db_conn
from audit import log_action


class TrucksPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # =========================
        # Page title
        # =========================
        title = QLabel("Truck Salok")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title)

        # =========================
        # Salok input section
        # =========================
        input_layout = QHBoxLayout()

        input_layout.addWidget(QLabel("Truck:"))
        self.truck_combo = QComboBox()
        self.truck_combo.currentTextChanged.connect(self.update_summary)
        input_layout.addWidget(self.truck_combo)

        input_layout.addWidget(QLabel("Drums:"))
        self.drums_input = QLineEdit()
        self.drums_input.setPlaceholderText("Enter number of drums")
        input_layout.addWidget(self.drums_input)

        add_btn = QPushButton("Add Salok")
        add_btn.clicked.connect(self.add_salok)
        input_layout.addWidget(add_btn)

        input_layout.addStretch()
        main_layout.addLayout(input_layout)
        # =========================
        # Refresh section
        # =========================
        refresh_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh Trucks")
        refresh_btn.clicked.connect(self.refresh_trucks)

        refresh_layout.addWidget(refresh_btn)
        refresh_layout.addStretch()

        main_layout.addLayout(refresh_layout)


        # =========================
        # Payment section
        # =========================
        payment_layout = QHBoxLayout()

        payment_layout.addWidget(QLabel("Payment (₱):"))
        self.payment_input = QLineEdit()
        self.payment_input.setPlaceholderText("Enter payment amount")
        payment_layout.addWidget(self.payment_input)

        pay_btn = QPushButton("Record Payment")
        pay_btn.clicked.connect(self.record_payment)
        payment_layout.addWidget(pay_btn)

        payment_layout.addStretch()
        main_layout.addLayout(payment_layout)

        # =========================
        # Truck summary (NEW)
        # =========================
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        main_layout.addWidget(self.summary_label)

        # =========================
        # Truck salok table
        # =========================
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Truck",
            "Drums",
            "Price / Drum",
            "Total (₱)",
            "Date",
            "Time"
        ])

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        main_layout.addWidget(self.table)

        self.load_trucks()
        self.load_logs()
        self.update_summary()
        
    def refresh(self):
        self.load_trucks()
        self.load_logs()


    # -------------------------------------------------
    # Load truck clients
    # -------------------------------------------------
    def load_trucks(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT name FROM clients
            WHERE LOWER(type) = 'truck'
            ORDER BY name
        """)
        rows = cur.fetchall()
        conn.close()

        self.truck_combo.clear()
        for r in rows:
            self.truck_combo.addItem(r["name"])

    # -------------------------------------------------
    # Load truck salok logs
    # -------------------------------------------------
    def load_logs(self):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT truck, drums, price, date, time
            FROM truck_saloks
            ORDER BY date DESC, time DESC
        """)
        rows = cur.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))

        for r, t in enumerate(rows):
            total = t["drums"] * t["price"]

            self.table.setItem(r, 0, QTableWidgetItem(t["truck"]))
            self.table.setItem(r, 1, QTableWidgetItem(str(t["drums"])))
            self.table.setItem(r, 2, QTableWidgetItem(f"₱{t['price']:.2f}"))
            self.table.setItem(r, 3, QTableWidgetItem(f"₱{total:.2f}"))
            self.table.setItem(r, 4, QTableWidgetItem(t["date"]))
            self.table.setItem(r, 5, QTableWidgetItem(t["time"]))

    # -------------------------------------------------
    # Compute and update truck summary (NEW)
    # -------------------------------------------------
    def update_summary(self):
        truck = self.truck_combo.currentText()
        if not truck:
            self.summary_label.setText("")
            return

        conn = get_db_conn()
        cur = conn.cursor()

        # Total charges
        cur.execute("""
            SELECT SUM(drums * price) AS total
            FROM truck_saloks
            WHERE truck = ?
        """, (truck,))
        charges = cur.fetchone()["total"] or 0

        # Total payments
        cur.execute("""
            SELECT SUM(amount) AS total
            FROM truck_payments
            WHERE truck = ?
        """, (truck,))
        payments = cur.fetchone()["total"] or 0

        conn.close()

        balance = charges - payments

        self.summary_label.setText(
            f"Total Charges: ₱{charges:.2f}   |   "
            f"Payments: ₱{payments:.2f}   |   "
            f"Outstanding Balance: ₱{balance:.2f}"
        )

    # -------------------------------------------------
    # Add truck salok (charge)
    # -------------------------------------------------
    def add_salok(self):
        truck = self.truck_combo.currentText()

        if not truck:
            QMessageBox.warning(self, "Select Truck", "Please select a truck.")
            return

        try:
            drums = int(self.drums_input.text())
            if drums <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Enter a valid number of drums.")
            return

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("SELECT value FROM settings WHERE key = 'PRICE_PER_DRUM'")
        row = cur.fetchone()
        price = float(row["value"]) if row else 0

        now = datetime.now()

        cur.execute("""
            INSERT INTO truck_saloks (truck, drums, price, date, time)
            VALUES (?, ?, ?, ?, ?)
        """, (
            truck,
            drums,
            price,
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S")
        ))

        conn.commit()
        conn.close()

        log_action(
            "SYSTEM",
            "Added truck salok",
            f"{truck}: {drums} drums (₱{drums * price:.2f})"
        )

        self.drums_input.clear()
        self.load_logs()
        self.update_summary()

        QMessageBox.information(
            self,
            "Salok Added",
            f"Truck: {truck}\nDrums: {drums}\nTotal: ₱{drums * price:.2f}"
        )

    # -------------------------------------------------
    # Record truck payment
    # -------------------------------------------------
    def record_payment(self):
        truck = self.truck_combo.currentText()

        if not truck:
            QMessageBox.warning(self, "Select Truck", "Please select a truck first.")
            return

        try:
            amount = float(self.payment_input.text())
            if amount <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Enter a valid payment amount.")
            return

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO truck_payments (truck, amount, date, note)
            VALUES (?, ?, ?, ?)
        """, (
            truck,
            amount,
            datetime.now().strftime("%Y-%m-%d"),
            "Truck payment"
        ))

        conn.commit()
        conn.close()

        log_action(
            "SYSTEM",
            "Recorded truck payment",
            f"{truck}: ₱{amount:.2f}"
        )

        self.payment_input.clear()
        self.update_summary()

        QMessageBox.information(
            self,
            "Payment Recorded",
            f"Payment of ₱{amount:.2f} recorded for {truck}."
        )
    def refresh_trucks(self):
        self.load_trucks()
        self.load_logs()
