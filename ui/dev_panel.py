"""Developer test panel — manually trigger states and verify reminders."""
import time
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QGroupBox, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from animation.state_machine import PetState

STATE_BUTTONS = [
    PetState.IDLE, PetState.MOUSE_NEAR, PetState.FOLLOW_MOUSE,
    PetState.SLEEP, PetState.WAKE_UP, PetState.CLICKED,
    PetState.DRAGGED, PetState.DROP, PetState.ANGRY,
    PetState.PURR, PetState.WALK, PetState.ALERT_SIT,
    PetState.ALERT_WATER,
]


class DevPanel(QWidget):
    """Floating debug panel for triggering pet states and viewing internal state."""

    def __init__(self, pet_window):
        super().__init__()
        self.pet = pet_window
        self.setWindowTitle("🎮 开发者测试面板")
        self.setFixedSize(380, 520)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Current state ──
        self.state_label = QLabel("当前状态: --")
        self.state_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2a2048;")
        layout.addWidget(self.state_label)

        # ── Animation triggers ──
        state_group = QGroupBox("动画触发")
        state_grid = QGridLayout(state_group)
        state_grid.setSpacing(4)
        for i, state in enumerate(STATE_BUTTONS):
            btn = QPushButton(state.value)
            btn.setStyleSheet(self._btn_style())
            btn.clicked.connect(lambda checked, s=state: self._trigger(s))
            state_grid.addWidget(btn, i // 4, i % 4)
        layout.addWidget(state_group)

        # ── Reminder tests ──
        reminder_group = QGroupBox("提醒测试")
        reminder_layout = QHBoxLayout(reminder_group)
        sit_btn = QPushButton("⚡ 立即久坐提醒")
        sit_btn.setStyleSheet(self._btn_style("#e8785a"))
        sit_btn.clicked.connect(lambda: self._trigger(PetState.ALERT_SIT, force=True))
        reminder_layout.addWidget(sit_btn)

        water_btn = QPushButton("💧 立即喝水提醒")
        water_btn.setStyleSheet(self._btn_style("#5a9ae8"))
        water_btn.clicked.connect(lambda: self._trigger(PetState.ALERT_WATER, force=True))
        reminder_layout.addWidget(water_btn)
        layout.addWidget(reminder_group)

        # ── Click counter test ──
        click_group = QGroupBox("点击测试")
        click_layout = QHBoxLayout(click_group)
        click_btn = QPushButton("👆 模拟点击")
        click_btn.setStyleSheet(self._btn_style("#8a7aff"))
        click_btn.clicked.connect(self._simulate_click)
        click_layout.addWidget(click_btn)

        reset_btn = QPushButton("🔄 重置计数器")
        reset_btn.setStyleSheet(self._btn_style())
        reset_btn.clicked.connect(self._reset_click_count)
        click_layout.addWidget(reset_btn)
        layout.addWidget(click_group)

        # ── Debug info ──
        info_group = QGroupBox("运行时信息")
        info_layout = QVBoxLayout(info_group)
        self._info_labels = {}
        for key in ["点击计数", "无操作计时", "透明度", "锁定剩余", "忽略剩余", "帧率"]:
            lbl = QLabel(f"{key}: --")
            lbl.setStyleSheet("font-size: 11px; color: #4a3a5a;")
            info_layout.addWidget(lbl)
            self._info_labels[key] = lbl
        layout.addWidget(info_group)

        # Close button
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_info)
        self._refresh_timer.start(200)

        self._start_time = time.time()

    def _btn_style(self, color="#6a5a8a"):
        return f"""
            QPushButton {{
                background: {color}; color: white; font-weight: bold;
                padding: 6px 8px; border-radius: 6px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {color}cc; }}
        """

    def _trigger(self, state: PetState, force=False):
        """Transition pet to a state."""
        if force:
            self.pet.state_machine._lock_until = 0

        # Show dialog for reminders so user knows it worked
        if state == PetState.ALERT_SIT:
            msg = QMessageBox(self)
            msg.setWindowTitle("⚡ 久坐提醒测试")
            msg.setText("已触发久坐提醒！\n\n宠物会播放 ALERT_SIT 动画，同时弹出系统通知。\n\n点击确定关闭通知测试。")
            msg.exec()
            self.pet._send_notification("⚡ [测试] 主人，起来动一动吧～")
        elif state == PetState.ALERT_WATER:
            msg = QMessageBox(self)
            msg.setWindowTitle("💧 喝水提醒测试")
            msg.setText("已触发喝水提醒！\n\n宠物会播放 ALERT_WATER 动画，同时弹出系统通知。\n\n点击确定关闭通知测试。")
            msg.exec()
            self.pet._send_notification("💧 [测试] 主人，记得喝水～")
        elif state == PetState.ANGRY:
            # Simulate 7 rapid clicks
            self.pet._click_count = 7
            from PyQt6.QtCore import QPointF, QEvent
            from PyQt6.QtGui import QMouseEvent
            for _ in range(7):
                event = QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    QPointF(250, 400), QPointF(250, 400),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                self.pet.mousePressEvent(event)

        self.pet.state_machine.transition(state)
        self.pet._last_activity = time.time()

    def _simulate_click(self):
        """Simulate a left click on the pet."""
        from PyQt6.QtCore import QPointF, QEvent
        from PyQt6.QtGui import QMouseEvent
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(250, 400),
            QPointF(250, 400),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        self.pet.mousePressEvent(event)

    def _reset_click_count(self):
        self.pet._click_count = 0
        self.pet._ignore_until = 0

    def _refresh_info(self):
        """Update debug labels."""
        pet = self.pet
        sm = pet.state_machine
        now = time.time()
        self.state_label.setText(f"当前状态: {sm.current.value}")

        self._info_labels["点击计数"].setText(f"点击计数: {pet._click_count}")
        inactive = now - pet._last_activity
        self._info_labels["无操作计时"].setText(f"无操作计时: {int(inactive // 60):02d}:{int(inactive % 60):02d}")
        self._info_labels["透明度"].setText(f"透明度: {pet.windowOpacity():.0%}")
        lock_left = max(0, sm._lock_until - now)
        self._info_labels["锁定剩余"].setText(f"状态锁定: {lock_left:.1f}s")
        ignore_left = max(0, pet._ignore_until - now)
        self._info_labels["忽略剩余"].setText(f"生气不理: {ignore_left:.1f}s")
        fps = 1.0 / max(0.03, now - self._start_time)
        self._info_labels["帧率"].setText(f"帧率: ~{fps:.0f} FPS")
        self._start_time = now

    def closeEvent(self, event):
        self._refresh_timer.stop()
        super().closeEvent(event)
