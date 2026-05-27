#!/usr/bin/env python3.12
"""DesktopPet - macOS desktop pet app
Upload your pet photo → AI recognizes species/size/color
→ pixel art pet appears on your desktop with matching colors
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app import PetApp

def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("DesktopPet")
    app.setOrganizationName("DesktopPet")

    # Global stylesheet
    app.setStyleSheet("""
        QToolTip {
            background: #2a2a3a;
            color: #e0e0e0;
            border: 1px solid #4a4a5a;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
        }
    """)

    window = PetApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
