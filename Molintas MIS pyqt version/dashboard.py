# dashboard.py
# Main dashboard window with sidebar and enhanced summary dashboard

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QPushButton,
    QVBoxLayout, QHBoxLayout, QLabel,
    QStackedWidget, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from datetime import date
from db import get_db_conn

from pages.clients import ClientsPage
from pages.billing import BillingPage
from pages.trucks import TrucksPage
from pages.reports import ReportsPage
from pages.settings import SettingsPage
from pages.users import UsersPage
from pages.audit_logs import AuditLogsPage   # ✅ ADD THIS
from audit import log_action


# ===================================================
# Dashboard Window
# ===================================================

class DashboardWindow(QMainWindow):
    def __init__(self, username, role, login_window):
        super().__init__()

        self.username = username
        self.role = role
        self.login_window = login_window

        self.setWindowTitle("Molintas Water Services MIS")
        self.resize(1100, 650)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ================= Sidebar =================
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background-color: #006d77;")
        sidebar_layout = QVBoxLayout(sidebar)

        title = QLabel("Molintas MIS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold; padding: 15px;"
        )
        sidebar_layout.addWidget(title)

        # ================= Content =================
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)

        self.page_title = QLabel()
        self.page_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(self.page_title)

        self.stack = QStackedWidget()

        # ================= Pages =================
        self.page_dashboard = DashboardSummaryPage(self)
        self.page_clients = ClientsPage()
        self.page_billing = BillingPage()
        self.page_trucks = TrucksPage()
        self.page_reports = ReportsPage()
        self.page_users = UsersPage()
        self.page_audit_logs = AuditLogsPage()     # ✅ ADD THIS
        self.page_settings = SettingsPage()

        # Add pages to stack
        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_clients)
        self.stack.addWidget(self.page_billing)
        self.stack.addWidget(self.page_trucks)
        self.stack.addWidget(self.page_reports)
        self.stack.addWidget(self.page_users)

        if self.role == "admin":
            self.stack.addWidget(self.page_audit_logs)   # ✅ ADD THIS
            self.stack.addWidget(self.page_settings)

        content_layout.addWidget(self.stack)

        # ================= Sidebar Buttons =================
        self.sidebar_buttons = {}

        self.add_btn(sidebar_layout, "Dashboard", self.page_dashboard)
        self.add_btn(sidebar_layout, "Clients", self.page_clients)
        self.add_btn(sidebar_layout, "Billing", self.page_billing)
        self.add_btn(sidebar_layout, "Truck Salok", self.page_trucks)
        self.add_btn(sidebar_layout, "Reports", self.page_reports)

        if self.role == "admin":
            self.add_btn(sidebar_layout, "Users", self.page_users)
            self.add_btn(sidebar_layout, "Audit Logs", self.page_audit_logs)  # ✅ BUTTON
            self.add_btn(sidebar_layout, "Settings", self.page_settings)

        sidebar_layout.addStretch()

        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("background-color: #83c5be; padding: 10px;")
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_widget)
        self.setCentralWidget(main_widget)

        self.switch_page("Dashboard", self.page_dashboard)

    # -------------------------------------------------
    # Sidebar helpers
    # -------------------------------------------------
    def add_btn(self, layout, name, page):
        btn = QPushButton(name)
        btn.clicked.connect(lambda: self.switch_page(name, page))
        btn.setStyleSheet(self.btn_style(False))
        layout.addWidget(btn)
        self.sidebar_buttons[name] = btn

    def switch_page(self, name, page):
        self.stack.setCurrentWidget(page)
        self.page_title.setText(f"Dashboard > {name}")

        if hasattr(page, "refresh"):
            page.refresh()
        elif hasattr(page, "load_clients"):
            page.load_clients()
        elif hasattr(page, "load_trucks"):
            page.load_trucks()
            page.load_logs()
        elif hasattr(page, "load_logs"):
            page.load_logs()

        for k, b in self.sidebar_buttons.items():
            b.setStyleSheet(self.btn_style(k == name))

    def btn_style(self, active):
        return (
            "background-color:#83c5be;color:black;font-weight:bold;padding:10px;text-align:left;"
            if active else
            "color:white;background:transparent;padding:10px;text-align:left;"
        )

    # -------------------------------------------------
    # Logout
    # -------------------------------------------------
    def logout(self):
        if QMessageBox.question(self, "Logout", "Logout?") == QMessageBox.StandardButton.Yes:
            log_action(self.username, "Logged out")
            self.close()
            self.login_window.show()


# ===================================================
# Clickable Card
# ===================================================

class ClickableCard(QFrame):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()


# ===================================================
# Dashboard Summary Page
# ===================================================

class DashboardSummaryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_dashboard = parent

        layout = QVBoxLayout(self)

        row1 = QHBoxLayout()
        self.cards = {}

        self.cards["unpaid"] = self.make_card("Unpaid Clients")
        self.cards["active"] = self.make_card("Active Clients")
        self.cards["inactive"] = self.make_card("Inactive Clients")
        self.cards["trucks_count"] = self.make_card("Total Trucks")

        for k in ["unpaid", "active", "inactive", "trucks_count"]:
            row1.addWidget(self.cards[k])

        row2 = QHBoxLayout()
        self.cards["clients_money"] = self.make_card("Client Receivables (₱)")
        self.cards["trucks_money"] = self.make_card("Truck Receivables (₱)")
        self.cards["today"] = self.make_card("Today's Collections (₱)")
        self.cards["month"] = self.make_card("This Month (₱)")

        for k in ["clients_money", "trucks_money", "today", "month"]:
            row2.addWidget(self.cards[k])

        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addStretch()

        # Click navigation
        self.cards["unpaid"].clicked.connect(lambda: self.goto("Clients"))
        self.cards["active"].clicked.connect(lambda: self.goto("Clients"))
        self.cards["inactive"].clicked.connect(lambda: self.goto("Clients"))
        self.cards["trucks_count"].clicked.connect(lambda: self.goto("Clients"))
        self.cards["clients_money"].clicked.connect(lambda: self.goto("Billing"))
        self.cards["trucks_money"].clicked.connect(lambda: self.goto("Truck Salok"))
        self.cards["today"].clicked.connect(lambda: self.goto("Reports"))
        self.cards["month"].clicked.connect(lambda: self.goto("Reports"))

    def make_card(self, title):
        frame = ClickableCard()
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.setStyleSheet(self.card_style("#222"))

        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setStyleSheet("color:#aaa;font-size:12px;")
        value = QLabel("0")
        value.setStyleSheet("font-size:22px;font-weight:bold;color:white;")

        layout.addWidget(label)
        layout.addWidget(value)
        frame.value_label = value
        return frame

    def refresh(self):
        conn = get_db_conn()
        cur = conn.cursor()
        today = date.today().strftime("%Y-%m-%d")

        cur.execute("""
            SELECT COUNT(*) FROM clients
            WHERE payment_status='Unpaid'
            AND status='Active'
            AND type IN ('household','apartment')
        """)
        unpaid = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM clients
            WHERE status='Active'
            AND type IN ('household','apartment')
        """)
        active = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM clients
            WHERE status='Inactive'
            AND type IN ('household','apartment')
        """)
        inactive = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM clients WHERE type='truck'")
        trucks_count = cur.fetchone()[0]

        cur.execute("""
            SELECT SUM(bill) FROM clients
            WHERE payment_status='Unpaid'
            AND status='Active'
            AND type IN ('household','apartment')
        """)
        clients_money = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(drums * price) FROM truck_saloks")
        trucks_money = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(amount) FROM payments WHERE date = ?", (today,))
        today_money = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT SUM(amount) FROM payments
            WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        """)
        month_money = cur.fetchone()[0] or 0

        conn.close()

        self.cards["unpaid"].value_label.setText(str(unpaid))
        self.cards["active"].value_label.setText(str(active))
        self.cards["inactive"].value_label.setText(str(inactive))
        self.cards["trucks_count"].value_label.setText(str(trucks_count))
        self.cards["clients_money"].value_label.setText(f"{clients_money:.2f}")
        self.cards["trucks_money"].value_label.setText(f"{trucks_money:.2f}")
        self.cards["today"].value_label.setText(f"{today_money:.2f}")
        self.cards["month"].value_label.setText(f"{month_money:.2f}")

    def goto(self, page_name):
        pages = {
            "Clients": self.parent_dashboard.page_clients,
            "Billing": self.parent_dashboard.page_billing,
            "Truck Salok": self.parent_dashboard.page_trucks,
            "Reports": self.parent_dashboard.page_reports,
            "Audit Logs": self.parent_dashboard.page_audit_logs,
        }
        self.parent_dashboard.switch_page(page_name, pages[page_name])

    def card_style(self, color):
        return f"""
        background:{color};
        border-radius:10px;
        padding:15px;
        """
