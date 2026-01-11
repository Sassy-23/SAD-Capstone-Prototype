# main.py
# This is the entry point of the application
# It only starts the app and shows the login window

import sys
from PyQt6.QtWidgets import QApplication
from login import LoginWindow


def main():
    # Every PyQt app needs exactly ONE QApplication
    app = QApplication(sys.argv)

    # Start with the login window
    login_window = LoginWindow()
    login_window.show()

    # Keep the app running
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
