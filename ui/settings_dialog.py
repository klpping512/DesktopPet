"""Settings dialog - adjust pet behavior and appearance"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QCheckBox, QPushButton, QGroupBox,
                             QSpinBox, QFormLayout, QDialogButtonBox, QWidget,
                             QStackedWidget)
from PyQt6.QtCore import Qt


class SettingsDialog(QDialog):
    """Settings dialog for DesktopPet"""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.setFixedSize(400, 480)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.result_settings = dict(settings)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Water reminder ──
        water_group = QGroupBox("💧 喝水提醒")
        water_form = QFormLayout(water_group)

        self._water_mode = QComboBox()
        self._water_mode.addItems(["按间隔", "按杯数"])
        current_mode = settings.get("water_mode", "interval")
        self._water_mode.setCurrentIndex(0 if current_mode == "interval" else 1)
        self._water_mode.currentIndexChanged.connect(self._on_water_mode_changed)
        water_form.addRow("提醒模式:", self._water_mode)

        self._water_interval = QSpinBox()
        self._water_interval.setRange(10, 180)
        self._water_interval.setValue(settings.get("water_interval_min", 60))
        self._water_interval.setSuffix(" 分钟")
        water_form.addRow("提醒间隔:", self._water_interval)

        self._water_cups = QSpinBox()
        self._water_cups.setRange(1, 20)
        self._water_cups.setValue(settings.get("water_cups_per_day", 8))
        self._water_cups.setSuffix(" 杯/天")
        water_form.addRow("每日杯数:", self._water_cups)

        # Show/hide based on mode
        self._on_water_mode_changed(self._water_mode.currentIndex())
        layout.addWidget(water_group)

        # ── Sit reminder ──
        sit_group = QGroupBox("🪑 久坐提醒")
        sit_form = QFormLayout(sit_group)

        self._sit_interval = QSpinBox()
        self._sit_interval.setRange(10, 180)
        self._sit_interval.setValue(settings.get("sit_interval_min", 45))
        self._sit_interval.setSuffix(" 分钟")
        sit_form.addRow("久坐提醒间隔:", self._sit_interval)
        layout.addWidget(sit_group)

        # ── Today pause ──
        pause_group = QGroupBox("⏸️ 今日暂停")
        pause_layout = QVBoxLayout(pause_group)
        self._water_paused = QCheckBox("今日暂停喝水提醒")
        self._water_paused.setChecked(settings.get("water_paused", False))
        pause_layout.addWidget(self._water_paused)

        self._sit_paused = QCheckBox("今日暂停久坐提醒")
        self._sit_paused.setChecked(settings.get("sit_paused", False))
        pause_layout.addWidget(self._sit_paused)

        hint = QLabel("快捷键: ^⇧P 一键暂停/恢复所有提醒")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        pause_layout.addWidget(hint)
        layout.addWidget(pause_group)

        # ── Display ──
        display_group = QGroupBox("显示")
        display_layout = QVBoxLayout(display_group)

        self._pixel_perfect = QCheckBox("像素风格（不抗锯齿）")
        self._pixel_perfect.setChecked(settings.get("pixel_perfect", False))
        display_layout.addWidget(self._pixel_perfect)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("停靠位置:"))
        self._pos_combo = QComboBox()
        self._pos_combo.addItems(["bottom_right", "bottom_left", "top_right", "top_left"])
        self._pos_combo.setCurrentText(settings.get("dock_position", "bottom_right"))
        pos_layout.addWidget(self._pos_combo)
        display_layout.addLayout(pos_layout)

        info_label = QLabel("ℹ️ 宠物大小会根据屏幕高度自动适配")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        display_layout.addWidget(info_label)
        layout.addWidget(display_group)

        # ── Buttons ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_water_mode_changed(self, idx):
        """Show/hide interval vs cups spinboxes."""
        is_cups = (idx == 1)
        self._water_interval.setVisible(not is_cups)
        self._water_cups.setVisible(is_cups)

    def _on_accept(self):
        """Save all settings to result."""
        s = self.result_settings
        s["water_mode"] = "cups" if self._water_mode.currentIndex() == 1 else "interval"
        s["water_cups_per_day"] = self._water_cups.value()
        s["water_interval_min"] = self._water_interval.value()
        s["sit_interval_min"] = self._sit_interval.value()
        s["water_paused"] = self._water_paused.isChecked()
        s["sit_paused"] = self._sit_paused.isChecked()
        s["pixel_perfect"] = self._pixel_perfect.isChecked()
        s["dock_position"] = self._pos_combo.currentText()
        self.accept()
