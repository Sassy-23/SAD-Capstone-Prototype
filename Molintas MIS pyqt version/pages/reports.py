# pages/reports.py
# Reports module
# Truck + Client Billing Reports (Daily → Annual)

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from datetime import date, timedelta
from db import get_db_conn
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from audit import log_action
import os


class ReportsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.mode = "daily"
        self.current_report_text = ""
        self.current_report_title = ""

        main_layout = QVBoxLayout(self)

        # =========================
        # Page title
        # =========================
        self.title = QLabel("Reports - Daily")
        self.title.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(self.title)

        # =========================
        # Buttons
        # =========================
        btn_layout = QHBoxLayout()

        for label, fn in [
            ("Daily", self.set_daily),
            ("Weekly", self.set_weekly),
            ("Monthly", self.set_monthly),
            ("Quarterly", self.set_quarterly),
            ("Annual", self.set_annual)
        ]:
            b = QPushButton(label)
            b.clicked.connect(fn)
            btn_layout.addWidget(b)

        btn_layout.addStretch()

        gen_btn = QPushButton("Generate Report")
        gen_btn.clicked.connect(self.generate_report)

        pdf_btn = QPushButton("Export to PDF")
        pdf_btn.clicked.connect(self.export_pdf)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_reports)

        btn_layout.addWidget(gen_btn)
        btn_layout.addWidget(pdf_btn)
        btn_layout.addWidget(refresh_btn)

        main_layout.addLayout(btn_layout)

        # =========================
        # Report display
        # =========================
        self.report_box = QTextEdit()
        self.report_box.setReadOnly(True)
        main_layout.addWidget(self.report_box)

        self.load_reports()

    # =========================
    # Mode switching
    # =========================
    def set_daily(self):
        self.mode = "daily"
        self.title.setText("Reports - Daily")
        self.load_reports()

    def set_weekly(self):
        self.mode = "weekly"
        self.title.setText("Reports - Weekly")
        self.load_reports()

    def set_monthly(self):
        self.mode = "monthly"
        self.title.setText("Reports - Monthly")
        self.load_reports()

    def set_quarterly(self):
        self.mode = "quarterly"
        self.title.setText("Reports - Quarterly")
        self.load_reports()

    def set_annual(self):
        self.mode = "annual"
        self.title.setText("Reports - Annual")
        self.load_reports()

    # =========================
    # Load report
    # =========================
    def load_reports(self):
        if self.mode == "daily":
            d = date.today().strftime("%Y-%m-%d")
            text = self.truck_report(d, d, "DAILY")
            text += "\n" + "=" * 50 + "\n\n"
            text += self.billing_daily_report(d)

        elif self.mode == "weekly":
            s, e = self.get_week_range()
            text = self.truck_report(s, e, "WEEKLY")
            text += "\n" + "=" * 50 + "\n\n"
            text += self.billing_weekly_report(s, e)

        elif self.mode == "monthly":
            s, e = self.get_month_range()
            text = self.truck_report(s, e, "MONTHLY")
            text += "\n" + "=" * 50 + "\n\n"
            text += self.billing_monthly_report(s, e)

        elif self.mode == "quarterly":
            s, e = self.get_quarter_range()
            text = self.truck_report(s, e, "QUARTERLY")
            text += "\n" + "=" * 50 + "\n\n"
            text += self.billing_quarterly_report(s, e)

        else:
            s, e = self.get_year_range()
            text = self.truck_report(s, e, "ANNUAL")
            text += "\n" + "=" * 50 + "\n\n"
            text += self.billing_annual_report(s, e)

        self.current_report_text = text
        self.report_box.setText(text)

    # =========================
    # Truck billing report (PER-TRUCK)
    # =========================
    def truck_report(self, start_date, end_date, label):
        conn = get_db_conn()
        cur = conn.cursor()

        # Overall totals
        cur.execute("""
            SELECT SUM(drums * price) AS charges
            FROM truck_saloks
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        total_charges = cur.fetchone()["charges"] or 0

        cur.execute("""
            SELECT SUM(amount) AS payments
            FROM truck_payments
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        total_payments = cur.fetchone()["payments"] or 0

        # Per-truck breakdown
        cur.execute("""
            SELECT
                t.truck,
                SUM(t.drums * t.price) AS charges,
                COALESCE(SUM(p.amount), 0) AS payments
            FROM truck_saloks t
            LEFT JOIN truck_payments p
                ON t.truck = p.truck
                AND p.date BETWEEN ? AND ?
            WHERE t.date BETWEEN ? AND ?
            GROUP BY t.truck
            ORDER BY t.truck
        """, (start_date, end_date, start_date, end_date))

        rows = cur.fetchall()
        conn.close()

        text = f"🚚 TRUCK BILLING - {label} REPORT\n"
        text += f"({start_date} to {end_date})\n"
        text += "-" * 50 + "\n"

        if total_charges == 0 and total_payments == 0:
            return text + "No truck transactions for this period.\n"

        text += f"Total Charges: ₱{total_charges:.2f}\n"
        text += f"Total Payments: ₱{total_payments:.2f}\n"
        text += f"Outstanding Balance: ₱{(total_charges - total_payments):.2f}\n\n"

        text += "Per Truck Breakdown:\n"
        for r in rows:
            bal = (r["charges"] or 0) - (r["payments"] or 0)
            text += (
                f"- {r['truck']}: "
                f"Charges ₱{r['charges']:.2f}, "
                f"Payments ₱{r['payments']:.2f}, "
                f"Balance ₱{bal:.2f}\n"
            )

        return text

    # =========================
    # Client billing reports (UNCHANGED)
    # =========================
    def billing_daily_report(self, d):
        return self._billing_range("DAILY", d, d)

    def billing_weekly_report(self, s, e):
        return self._billing_range("WEEKLY", s, e)

    def billing_monthly_report(self, s, e):
        return self._billing_range("MONTHLY", s, e)

    def billing_quarterly_report(self, s, e):
        return self._billing_range("QUARTERLY", s, e)

    def billing_annual_report(self, s, e):
        return self._billing_range("ANNUAL", s, e)

    def _billing_range(self, label, start_date, end_date):
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT SUM(usage) AS usage, SUM(bill) AS bill
            FROM clients
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        b = cur.fetchone()

        cur.execute("""
            SELECT SUM(amount) AS paid
            FROM payments
            WHERE date BETWEEN ? AND ?
        """, (start_date, end_date))
        p = cur.fetchone()

        conn.close()

        text = f"💧 CLIENT BILLING - {label} REPORT\n"
        text += f"({start_date} to {end_date})\n"
        text += "-" * 50 + "\n"
        text += f"Usage Added: {b['usage'] or 0} m³\n"
        text += f"Billing Added: ₱{b['bill'] or 0:.2f}\n"
        text += f"Payments Collected: ₱{p['paid'] or 0:.2f}\n"

        return text

    # =========================
    # Date helpers
    # =========================
    def get_week_range(self):
        t = date.today()
        s = t - timedelta(days=t.weekday())
        return s.strftime("%Y-%m-%d"), (s + timedelta(days=6)).strftime("%Y-%m-%d")

    def get_month_range(self):
        t = date.today()
        s = t.replace(day=1)
        e = (s.replace(month=s.month % 12 + 1, day=1) - timedelta(days=1))
        return s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")

    def get_quarter_range(self):
        t = date.today()
        q = (t.month - 1) // 3
        s = date(t.year, q * 3 + 1, 1)
        e = (date(t.year, q * 3 + 4, 1) - timedelta(days=1))
        return s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")

    def get_year_range(self):
        y = date.today().year
        return f"{y}-01-01", f"{y}-12-31"

    # =========================
    # Export / logging
    # =========================
    def generate_report(self):
        self.current_report_title = self.title.text()
        QMessageBox.information(self, "Report Ready", "You can now export the report.")

    def export_pdf(self):
        if not self.current_report_text:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if not path:
            return
        if not path.endswith(".pdf"):
            path += ".pdf"

        c = canvas.Canvas(path, pagesize=A4)
        w, h = A4
        y = h - inch

        c.setFont("Helvetica-Bold", 14)
        c.drawString(inch, y, self.current_report_title)
        y -= 30
        c.setFont("Helvetica", 10)

        for line in self.current_report_text.split("\n"):
            if y < inch:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = h - inch
            c.drawString(inch, y, line)
            y -= 14

        c.save()
