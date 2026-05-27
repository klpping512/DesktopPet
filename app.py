"""Application entry point - manages window, tray, and global state"""
import os
import json
from PyQt6.QtWidgets import QMainWindow, QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtCore import Qt, QTimer
from pet_window import PetWindow
from ui.settings_dialog import SettingsDialog
from ui.upload_dialog import UploadDialog

SETTINGS_PATH = os.path.expanduser("~/.desktoppet_settings.json")

DEFAULT_SETTINGS = {
    "water_mode": "interval",
    "water_cups_per_day": 8,
    "water_interval_min": 60,
    "sit_interval_min": 45,
    "water_paused": False,
    "sit_paused": False,
    "dock_position": "bottom_right",
    "pixel_perfect": False,
    "auto_launch": False,
}


class PetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = self._load_settings()
        self.pet_window = None
        self.tray_icon = None
        self.pet_data = None  # Vision API result

        self.setWindowTitle("DesktopPet")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(1, 1)  # Hidden main window

        self._setup_tray()

        # Show upload dialog on first launch
        QTimer.singleShot(500, self._check_first_launch)

    def _load_settings(self):
        try:
            with open(SETTINGS_PATH) as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except:
            return dict(DEFAULT_SETTINGS)

    def _save_settings(self):
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(self.settings, f, indent=2)

    def _setup_tray(self):
        # Create a simple tray icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("DesktopPet")

        menu = QMenu()

        change_action = QAction("📷 更换宠物", self)
        change_action.triggered.connect(self._show_upload)
        menu.addAction(change_action)

        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        self._toggle_pet_action = QAction("🙈 隐藏宠物", self)
        self._toggle_pet_action.triggered.connect(self._toggle_pet_visibility)
        menu.addAction(self._toggle_pet_action)

        menu.addSeparator()

        snooze_sit_action = QAction("🪑 推迟久坐提醒", self)
        snooze_sit_action.triggered.connect(self._shortcut_snooze_sit)
        menu.addAction(snooze_sit_action)

        snooze_water_action = QAction("💧 推迟喝水提醒", self)
        snooze_water_action.triggered.connect(self._shortcut_snooze_water)
        menu.addAction(snooze_water_action)

        self._pause_action = QAction("⏸️ 暂停提醒", self)
        self._pause_action.triggered.connect(self._shortcut_toggle_pause)
        menu.addAction(self._pause_action)

        menu.addSeparator()

        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        quit_action = QAction("🚪 退出", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def _activate_app(self):
        """Bring app to front on macOS."""
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            QApplication.instance().activateWindow()

    def _shortcut_snooze_sit(self):
        if self.pet_window:
            self.pet_window.snooze_sit()
            self.tray_icon.showMessage("DesktopPet",
                                       "🪑 久坐提醒已推迟 10 分钟",
                                       QSystemTrayIcon.MessageIcon.Information, 3000)

    def _shortcut_snooze_water(self):
        if self.pet_window:
            self.pet_window.snooze_water()
            self.tray_icon.showMessage("DesktopPet",
                                       "💧 喝水提醒已推迟 10 分钟",
                                       QSystemTrayIcon.MessageIcon.Information, 3000)

    def _shortcut_toggle_pause(self):
        s = self.settings
        both_paused = s.get("water_paused") and s.get("sit_paused")
        s["water_paused"] = not both_paused
        s["sit_paused"] = not both_paused
        if self.pet_window:
            self.pet_window._sit_timer = 0
            self.pet_window._water_timer = 0
        self._save_settings()
        label = "已暂停所有提醒" if s["water_paused"] else "已恢复所有提醒"
        if self.tray_icon:
            self.tray_icon.showMessage("DesktopPet",
                                       label,
                                       QSystemTrayIcon.MessageIcon.Information, 3000)

    def _toggle_pet_visibility(self):
        if self.pet_window:
            hidden = self.pet_window.toggle_visibility()
            self._toggle_pet_action.setText("🐱 显示宠物" if hidden else "🙈 隐藏宠物")

    def _check_first_launch(self):
        if not self.pet_data:
            self._show_upload()

    def _show_upload(self):
        self._activate_app()
        dialog = UploadDialog(None)
        if dialog.exec():
            self.pet_data = dialog.result_data
            self._spawn_pet()

    def _spawn_pet(self):
        if self.pet_window:
            self.pet_window.close()
            self.pet_window.deleteLater()

        self.pet_window = PetWindow(self.pet_data, self.settings)
        self.pet_window._app = self  # Store reference without Qt parent
        self.pet_window.show()

        if self.tray_icon:
            self.tray_icon.showMessage(
                "DesktopPet",
                f"🐾 {self.pet_data.get('species', '宠物').title()} 已来到你的桌面！",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )

    def _show_settings(self):
        self._activate_app()
        dialog = SettingsDialog(self.settings, None)
        if dialog.exec():
            self.settings.update(dialog.result_settings)
            self._save_settings()
            if self.pet_window:
                self.pet_window.apply_settings(self.settings)

    def _show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(self, "关于 DesktopPet",
                          "DesktopPet v2.0\n\n"
                          "上传你家宠物的照片，\n"
                          "让它变成像素风桌面小伙伴\n"
                          "陪你工作、提醒你喝水休息。\n\n"
                          "MIT License · 开源公益项目")

    def _quit(self):
        if self.pet_window:
            self.pet_window.close()
        QApplication.quit()
