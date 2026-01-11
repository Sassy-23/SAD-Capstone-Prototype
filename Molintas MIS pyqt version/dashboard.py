# dashboard.py
# Main dashboard window with sidebar and summary dashboard

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

        # Pages
        self.page_dashboard = DashboardSummaryPage(self)
        self.page_clients = ClientsPage()
        self.page_billing = BillingPage()
        self.page_trucks = TrucksPage()
        self.page_reports = ReportsPage()
        self.page_users = UsersPage()
        self.page_settings = SettingsPage()

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_clients)
        self.stack.addWidget(self.page_billing)
        self.stack.addWidget(self.page_trucks)
        self.stack.addWidget(self.page_reports)
        self.stack.addWidget(self.page_users)

        if self.role == "admin":
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

    # ---------------- Sidebar Helpers ----------------
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

        for k, b in self.sidebar_buttons.items():
            b.setStyleSheet(self.btn_style(k == name))

    def btn_style(self, active):
        return (
            "background-color:#83c5be;color:black;font-weight:bold;padding:10px;text-align:left;"
            if active else
            "color:white;background:transparent;padding:10px;text-align:left;"
        )

    # ---------------- Logout ----------------
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

        cards_layout = QHBoxLayout()
        self.cards = {}

        self.cards["unpaid"] = self.make_card("Unpaid Clients")
        self.cards["clients"] = self.make_card("Client Receivables (₱)")
        self.cards["trucks"] = self.make_card("Truck Receivables (₱)")
        self.cards["today"] = self.make_card("Today's Collections (₱)")

        for c in self.cards.values():
            cards_layout.addWidget(c)

        layout.addLayout(cards_layout)
        layout.addStretch()

        # Click behavior
        self.cards["unpaid"].clicked.connect(lambda: self.goto("Clients"))
        self.cards["clients"].clicked.connect(lambda: self.goto("Billing"))
        self.cards["trucks"].clicked.connect(lambda: self.goto("Truck Salok"))
        self.cards["today"].clicked.connect(lambda: self.goto("Reports"))

    # ---------------- Create card ----------------
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

    # ---------------- Refresh data ----------------
    def refresh(self):
        conn = get_db_conn()
        cur = conn.cursor()
        today = date.today().strftime("%Y-%m-%d")

        # Unpaid (ACTIVE only)
        cur.execute("""
            SELECT COUNT(*) FROM clients
            WHERE payment_status='Unpaid' AND status='Active'
        """)
        unpaid = cur.fetchone()[0]

        # Overdue
        cur.execute("""
            SELECT COUNT(*) FROM clients
            WHERE payment_status='Unpaid'
            AND status='Active'
            AND date IS NOT NULL
            AND date < ?
        """, (today,))
        overdue = cur.fetchone()[0]

        # Client receivables
        cur.execute("""
            SELECT SUM(bill) FROM clients
            WHERE payment_status='Unpaid' AND status='Active'
        """)
        client_total = cur.fetchone()[0] or 0

        # Truck receivables
        cur.execute("SELECT SUM(drums * price) FROM truck_saloks")
        truck_total = cur.fetchone()[0] or 0

        # Today collections
        cur.execute("""
            SELECT SUM(amount) FROM payments
            WHERE date = ?
        """, (today,))
        today_total = cur.fetchone()[0] or 0

        conn.close()

        self.cards["unpaid"].value_label.setText(str(unpaid))
        self.cards["clients"].value_label.setText(f"{client_total:.2f}")
        self.cards["trucks"].value_label.setText(f"{truck_total:.2f}")
        self.cards["today"].value_label.setText(f"{today_total:.2f}")

        if overdue > 0:
            self.cards["unpaid"].setStyleSheet(self.card_style("#7a1f1f"))
        else:
            self.cards["unpaid"].setStyleSheet(self.card_style("#222"))

    # ---------------- Navigation ----------------
    def goto(self, name):
        pages = {
            "Clients": self.parent_dashboard.page_clients,
            "Billing": self.parent_dashboard.page_billing,
            "Truck Salok": self.parent_dashboard.page_trucks,
            "Reports": self.parent_dashboard.page_reports,
        }
        self.parent_dashboard.switch_page(name, pages[name])

    def card_style(self, color):
        return f"""
        background:{color};
        border-radius:10px;
        padding:15px;
        """
