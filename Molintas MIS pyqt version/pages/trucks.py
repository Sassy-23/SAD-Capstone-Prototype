# pages/trucks.py
# Truck Salok module
# Handles truck water collection, payments, and balance computation
# WITH date + truck filtering (history preserved)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QLineEdit, QPushButton, QMessageBox,
    QComboBox, QDateEdit
)
from PyQt6.QtCore import Qt, QDate
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
        # Filter section (NEW)
        # =========================
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.from_date)

        filter_layout.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        filter_layout.addWidget(self.to_date)

        today_btn = QPushButton("Today")
        today_btn.clicked.connect(self.filter_today)
        filter_layout.addWidget(today_btn)

        apply_btn = QPushButton("Apply Filter")
        apply_btn.clicked.connect(self.load_logs)
        filter_layout.addWidget(apply_btn)

        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_btn)

        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

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
        # Truck summary
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
        self.truck_combo.addItem("All Trucks")
        for r in rows:
            self.truck_combo.addItem(r["name"])

    # -------------------------------------------------
    # Load truck salok logs (FILTERED)
    # -------------------------------------------------
    def load_logs(self):
        conn = get_db_conn()
        cur = conn.cursor()

        query = """
            SELECT truck, drums, price, date, time
            FROM truck_saloks
            WHERE date BETWEEN ? AND ?
        """
        params = [
            self.from_date.date().toString("yyyy-MM-dd"),
            self.to_date.date().toString("yyyy-MM-dd")
        ]

        if self.truck_combo.currentText() != "All Trucks":
            query += " AND truck = ?"
            params.append(self.truck_combo.currentText())

        query += " ORDER BY date DESC, time DESC"

        cur.execute(query, params)
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
    # Update truck summary
    # -------------------------------------------------
    def update_summary(self):
        truck = self.truck_combo.currentText()

        if not truck or truck == "All Trucks":
            self.summary_label.setText("")
            return

        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT SUM(drums * price) AS total
            FROM truck_saloks
            WHERE truck = ?
        """, (truck,))
        charges = cur.fetchone()["total"] or 0

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
    # Add truck salok
    # -------------------------------------------------
    def add_salok(self):
        truck = self.truck_combo.currentText()

        if truck in ("", "All Trucks"):
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

    # -------------------------------------------------
    # Record truck payment
    # -------------------------------------------------
    def record_payment(self):
        truck = self.truck_combo.currentText()

        if truck in ("", "All Trucks"):
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

    # -------------------------------------------------
    # Filter helpers
    # -------------------------------------------------
    def filter_today(self):
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today)
        self.load_logs()

    def clear_filters(self):
        today = QDate.currentDate()
        self.from_date.setDate(today)
        self.to_date.setDate(today)
        self.truck_combo.setCurrentIndex(0)
        self.load_logs()
