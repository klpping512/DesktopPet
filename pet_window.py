"""Pet overlay window - transparent, always-on-top, follows mouse"""
import math
import time
import random
import sys
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QPixmap, QTransform, QMouseEvent
from PyQt6.QtCore import Qt, QTimer, QRectF, QPoint, QSize, QPropertyAnimation, pyqtProperty

from animation.state_machine import PetState, StateMachine
from animation.sprites import SpriteRenderer
from utils.color_palette import apply_color_palette
from utils.asset_loader import AssetLoader


class PetWindow(QWidget):
    WIDTH = 300
    HEIGHT = 300

    def __init__(self, pet_data, settings, parent=None):
        super().__init__(parent)
        self.pet_data = pet_data
        self.settings = settings
        self._app = None  # Set by PetApp after creation
        self._dragging = False
        self._drag_offset = QPoint()
        self._mouse_pos = QPoint(self.WIDTH // 2, self.HEIGHT // 2)
        self._last_activity = time.time()
        self._hidden = False
        self._nswindow = None  # cached NSWindow pointer for orderFront:

        # Click reaction system
        self._click_count = 0
        self._click_reset_timer = 0.0
        self._ignore_until = 0.0

        # Purr timer — mouse stays on cat 2s → purr
        self._purr_timer = QTimer(self)
        self._purr_timer.setSingleShot(True)
        self._purr_timer.timeout.connect(self._trigger_purr)

        # Auto-wander system
        self._auto_timer = 0.0
        self._auto_interval = random.uniform(8, 15)
        self._wander_target_x = None  # target X for walk movement
        self._walk_speed = 80  # pixels/sec

        # Keep-on-top counter (periodic orderFront without activation)
        self._top_tick = 0

        # Setup transparent window - floating but never steals focus
        self.setWindowTitle("DesktopPet")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        # Position at bottom-right by default
        self._position_window()

        # Idle fade — 5s no interaction → 40% opacity
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(800)
        self._fade_check_timer = QTimer(self)
        self._fade_check_timer.timeout.connect(self._check_idle_fade)
        self._fade_check_timer.start(1000)

        # Load and colorize sprites
        species = pet_data.get("species", "cat")
        size = pet_data.get("size_group", "medium")
        primary = pet_data.get("primary_color", "orange")
        secondary = pet_data.get("secondary_color", None)

        # Resolve variation name from recognition + pattern
        from vision.pet_recognizer import PetAnalyzer
        if "variation_name" in pet_data:
            variation = pet_data["variation_name"]
        else:
            variation = PetAnalyzer.resolve_variation(pet_data)
        pet_data["variation_name"] = variation

        self.loader = AssetLoader(species, size, variation)
        if self.loader.is_precolored:
            self.sprites = self.loader.get_sprites()  # Already colored
        else:
            self.sprites = apply_color_palette(self.loader.get_sprites(), primary, secondary)
        self.renderer = SpriteRenderer(self.sprites)

        # State machine
        self.state_machine = StateMachine()

        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(33)  # ~30 FPS

        # Idle → Sleep timer
        self._sleep_timer = 0
        self._last_state_check = time.time()

        # Alert timers
        self._sit_timer = 0
        self._water_timer = 0
        self._snooze_sit_until = 0
        self._snooze_water_until = 0
        self._apply_alert_intervals(settings)

        # Set initial scale (adaptive)
        self.renderer.set_scale(self._compute_scale())

        # Set mouse tracking
        self.setMouseTracking(True)

    def showEvent(self, event):
        """Called when window is first shown — winId() is valid here."""
        super().showEvent(event)
        if sys.platform == "darwin" and self._nswindow is None:
            self._set_mac_floating_level()

    def _position_window(self):
        screen = self.screen()
        if not screen:
            return
        geo = screen.availableGeometry()
        pos = self.settings.get("dock_position", "bottom_right")
        if pos == "bottom_right":
            self.move(geo.right() - self.WIDTH, geo.bottom() - self.HEIGHT)
        elif pos == "bottom_left":
            self.move(geo.left(), geo.bottom() - self.HEIGHT)
        elif pos == "top_right":
            self.move(geo.right() - self.WIDTH, geo.top())
        elif pos == "top_left":
            self.move(geo.left(), geo.top())

    def apply_settings(self, settings):
        self.settings = settings
        self._apply_alert_intervals(settings)
        self.renderer.set_scale(self._compute_scale())
        self.update()

    def _apply_alert_intervals(self, settings):
        """Compute water/sit intervals from settings (supports cups & interval modes)."""
        self._sit_interval = settings.get("sit_interval_min", 45) * 60
        water_mode = settings.get("water_mode", "interval")
        if water_mode == "cups":
            cups = settings.get("water_cups_per_day", 8)
            # Assume ~9 active hours → interval = 9h / cups
            if cups > 0:
                self._water_interval = max(20, int(9 * 3600 / cups))  # min 20min
            else:
                self._water_interval = 3600
        else:
            self._water_interval = settings.get("water_interval_min", 60) * 60

    def snooze_sit(self):
        """Snooze sit reminder for 10 minutes."""
        self._snooze_sit_until = time.time() + 600

    def snooze_water(self):
        """Snooze water reminder for 10 minutes."""
        self._snooze_water_until = time.time() + 600

    def _compute_scale(self):
        """Adaptive scale based on screen height — larger screen = bigger pet"""
        screen = self.screen()
        if not screen:
            return 3.0
        h = screen.availableGeometry().height()
        if h < 900:
            return 3.0
        elif h < 1200:
            return 4.0
        elif h < 1440:
            return 5.0
        else:
            return 6.0

    def _set_mac_floating_level(self):
        """Set window to float above ALL windows without stealing focus.
        Called from showEvent (after winId() is valid)."""
        try:
            import ctypes
            import ctypes.util

            libobjc = ctypes.cdll.LoadLibrary(
                ctypes.util.find_library("objc") or "/usr/lib/libobjc.dylib"
            )
            ctypes.cdll.LoadLibrary(
                ctypes.util.find_library("AppKit")
                or "/System/Library/Frameworks/AppKit.framework/AppKit"
            )

            _msgSend = libobjc.objc_msgSend
            _msgSend.restype = None
            _msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

            _sel = libobjc.sel_registerName
            _sel.restype = ctypes.c_void_p
            _sel.argtypes = [ctypes.c_char_p]

            # winId() is valid here (called from showEvent)
            wid = int(self.winId())
            if wid == 0:
                return
            nsview = ctypes.c_void_p(wid)
            sel_window = _sel(b"window")
            _msgSend.restype = ctypes.c_void_p
            nswindow = _msgSend(nsview, sel_window)
            if not nswindow:
                return

            self._nswindow = nswindow  # Cache for periodic orderFront:
            # Cache ctypes handles to avoid re-loading every 3s
            self._ctypes_libobjc = libobjc
            self._ctypes_sel = _sel
            self._ctypes_msgSend = _msgSend

            # NSStatusWindowLevel = 25 — above all application windows
            _msgSend.restype = None
            _msgSend(nswindow, _sel(b"setLevel:"), 25)
            # All spaces
            _msgSend(nswindow, _sel(b"setCollectionBehavior:"), 1 << 8)
        except Exception:
            self._nswindow = None

    def _keep_on_top(self):
        """Periodic reorder to front WITHOUT activation.
        Uses [NSWindow orderFront:] which does NOT steal keyboard focus."""
        if self._nswindow is None or self._hidden:
            return
        try:
            _msgSend = self._ctypes_msgSend
            sel = self._ctypes_sel
            # orderFront: — reorder without activation
            _msgSend.restype = None
            _msgSend(self._nswindow, sel(b"orderFront:"), 0)
        except Exception:
            pass

    def toggle_visibility(self):
        """Show or hide the pet"""
        self._hidden = not self._hidden
        if self._hidden:
            self.hide()
        else:
            self.show()
        return self._hidden

    def is_hidden(self):
        return self._hidden

    # ── Mouse Events ──

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            now = time.time()
            self._last_activity = now

            # During angry ignore period — do nothing
            if now < self._ignore_until:
                return

            self._click_count += 1
            self._click_reset_timer = 0
            self._dragging = True
            self._drag_offset = event.position().toPoint()

            if self._click_count >= 7:
                # 7+ clicks → angry, 5s ignore
                self.state_machine.transition(PetState.ANGRY)
                self._ignore_until = now + 5.0
                self._click_count = 0
            elif self._click_count >= 5:
                # 5-6 clicks → attack (angry state, shorter)
                self.state_machine.transition(PetState.ANGRY)
            elif self._click_count >= 3:
                # 3-4 clicks → hurt animation via dragged
                self.state_machine.transition(PetState.DRAGGED)
                QTimer.singleShot(400, lambda: self.state_machine.transition(PetState.DROP))
            else:
                # 1-2 clicks → happy jump
                self.state_machine.transition(PetState.CLICKED)
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        self._mouse_pos = event.position().toPoint()
        self._last_activity = time.time()

        if self._dragging:
            self.move(self.mapToGlobal(event.position().toPoint() - self._drag_offset))
            self.state_machine.transition(PetState.DRAGGED)
        else:
            # Check if mouse is near
            center = QPoint(self.WIDTH // 2, self.HEIGHT)
            dist = math.hypot(
                event.position().x() - center.x(),
                event.position().y() - center.y()
            )
            if dist < 120:
                # Mouse near → start purr timer (2s hold for purr)
                current = self.state_machine.current
                if current not in (PetState.ANGRY, PetState.PURR, PetState.DRAGGED):
                    if not self._purr_timer.isActive():
                        self._purr_timer.start(2000)
                self.state_machine.transition(PetState.MOUSE_NEAR)
            else:
                self._purr_timer.stop()
                if self.state_machine.current == PetState.PURR:
                    self.state_machine.transition(PetState.IDLE)
                self.state_machine.transition(PetState.IDLE)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            self._dragging = False
            self.state_machine.transition(PetState.DROP)

    def _show_context_menu(self, event):
        from PyQt6.QtWidgets import QMenu, QSystemTrayIcon
        menu = QMenu()
        app = self._app
        menu.addAction("📷 更换宠物", lambda: app._show_upload() if app else None)
        menu.addAction("🎮 测试模式", lambda: self._open_dev_panel())
        menu.addAction("⚙️ 设置", lambda: app._show_settings() if app else None)
        menu.addSeparator()
        if not self._hidden:
            menu.addAction("🙈 隐藏宠物", lambda: self._hide_from_menu())
        else:
            menu.addAction("🐱 显示宠物", lambda: self._show_from_menu())
        menu.addSeparator()
        menu.addAction("🚪 退出", lambda: app._quit() if app else None)
        menu.exec(self.mapToGlobal(event.position().toPoint()))

    def _open_dev_panel(self):
        """Open developer test panel"""
        from ui.dev_panel import DevPanel
        self._dev_panel = DevPanel(self)
        self._dev_panel.show()

    def _hide_from_menu(self):
        self.toggle_visibility()
        if self._app and self._app.tray_icon:
            self._app.tray_icon.showMessage("DesktopPet", "🐱 宠物已隐藏，点击托盘图标可重新显示",
                                            QSystemTrayIcon.MessageIcon.Information, 2000)

    def _show_from_menu(self):
        self.toggle_visibility()

    # ── Idle Fade ──

    def _check_idle_fade(self):
        """Fade to 40% after 5s inactivity, restore on interaction"""
        inactive = time.time() - self._last_activity
        if inactive > 5 and self.windowOpacity() > 0.45:
            self._fade_anim.stop()
            self._fade_anim.setEndValue(0.4)
            self._fade_anim.start()
        elif inactive <= 5 and self.windowOpacity() < 0.95:
            self._fade_anim.stop()
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.start()

    def _trigger_purr(self):
        """Mouse has been near for 2s → purr"""
        if self.state_machine.current in (PetState.MOUSE_NEAR, PetState.IDLE):
            self.state_machine.transition(PetState.PURR)

    # ── Auto-Wander ──

    def _trigger_auto_behavior(self):
        """Randomly pick a behavior: sit, idle, walk left/right."""
        if self.state_machine.current not in (PetState.IDLE, PetState.MOUSE_NEAR):
            return
        roll = random.random()
        if roll < 0.3:
            # Sit for a bit
            self.state_machine.transition(PetState.SIT)
            QTimer.singleShot(random.randint(3000, 6000),
                              lambda: self.state_machine.transition(PetState.IDLE))
        elif roll < 0.5:
            # Wander left
            self._wander_target_x = max(0, self.x() - random.randint(50, 200))
            self.state_machine.facing_right = False
            self.state_machine.transition(PetState.WALK)
        elif roll < 0.7:
            # Wander right
            screen = self.screen()
            max_x = (screen.availableGeometry().width() - 50) if screen else 1200
            self._wander_target_x = min(max_x, self.x() + random.randint(50, 200))
            self.state_machine.facing_right = True
            self.state_machine.transition(PetState.WALK)
        elif roll < 0.85:
            # Play animation
            self.state_machine.transition(PetState.PLAY)
            QTimer.singleShot(random.randint(1500, 3000),
                              lambda: self.state_machine.transition(PetState.IDLE))
        else:
            pass  # Stay idle — blink animation plays automatically

    def _walk_move(self, dt):
        """Move window toward wander target."""
        if self._wander_target_x is None:
            return
        cx, cy = self.x(), self.y()
        dx = self._wander_target_x - cx
        step = self._walk_speed * dt
        if abs(dx) < step:
            self.move(self._wander_target_x, cy)
        else:
            self.move(int(cx + (step if dx > 0 else -step)), cy)

    # ── Animation Loop ──

    def _tick(self):
        now = time.time()
        dt = now - self._last_state_check
        self._last_state_check = now

        # Periodic keep-on-top (every 3s, reorder without activation)
        self._top_tick += dt
        if self._top_tick > 3.0:
            self._top_tick = 0
            self._keep_on_top()

        # Click counter: reset after 30s no clicks
        self._click_reset_timer += dt
        if self._click_reset_timer > 30 and self._click_count > 0:
            self._click_count = 0

        current = self.state_machine.current

        # Sleep detection
        if current != PetState.SLEEP and (now - self._last_activity) > 30:
            self.state_machine.transition(PetState.SLEEP)
        elif current == PetState.SLEEP and (now - self._last_activity) <= 30:
            self.state_machine.transition(PetState.WAKE_UP)

        # Alert timers (respect snooze & pause)
        if current not in (PetState.ALERT_SIT, PetState.ALERT_WATER, PetState.SLEEP):
            sit_paused = self.settings.get("sit_paused", False)
            water_paused = self.settings.get("water_paused", False)

            if not sit_paused:
                self._sit_timer += dt
                if now < self._snooze_sit_until:
                    self._sit_timer = 0
                if self._sit_timer >= self._sit_interval:
                    self._sit_timer = 0
                    self.state_machine.transition(PetState.ALERT_SIT)
                    self._send_notification("主人，起来动一动吧～")

            if not water_paused:
                self._water_timer += dt
                if now < self._snooze_water_until:
                    self._water_timer = 0
                if self._water_timer >= self._water_interval:
                    self._water_timer = 0
                    self.state_machine.transition(PetState.ALERT_WATER)
                    self._send_notification("主人，记得喝水～")

        # ── Auto-wander behavior ──
        if current in (PetState.IDLE, PetState.MOUSE_NEAR) and (now - self._last_activity) < 30:
            self._auto_timer += dt
            if self._auto_timer >= self._auto_interval:
                self._auto_timer = 0
                self._auto_interval = random.uniform(8, 15)
                self._trigger_auto_behavior()

        # ── WALK movement ──
        if current == PetState.WALK:
            self._walk_move(dt)
            if self._wander_target_x is not None:
                cx = self.x()
                dist_left = abs(self._wander_target_x - cx)
                if dist_left < 5:
                    self._wander_target_x = None
                    self.state_machine.transition(PetState.IDLE)

        # Follow mouse (when mouse is moving slowly in front)
        if current == PetState.MOUSE_NEAR:
            center = QPoint(self.WIDTH // 2, self.HEIGHT)
            dx = self._mouse_pos.x() - center.x()
            if 120 < math.hypot(dx, self._mouse_pos.y() - center.y()) < 200:
                self.state_machine.transition(PetState.FOLLOW_MOUSE)

        self.renderer.update(current, dt)
        self.update()

    def _send_notification(self, message):
        try:
            from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
            # Find tray icon from the QApplication's top-level widgets
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'tray_icon') and widget.tray_icon:
                    widget.tray_icon.showMessage("DesktopPet", message,
                                                 QSystemTrayIcon.MessageIcon.Information, 5000)
                    return
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        pixel_perfect = self.settings.get("pixel_perfect", False)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, not pixel_perfect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, not pixel_perfect)

        frame = self.renderer.get_current_frame()
        if frame and not frame.isNull():
            # Center horizontally, sit at bottom
            x = (self.WIDTH - frame.width()) // 2
            y = self.HEIGHT - frame.height() - 10

            # Flip based on facing direction
            if self.state_machine.facing_right:
                painter.drawPixmap(x, y, frame)
            else:
                transform = QTransform().scale(-1, 1)
                flipped = frame.transformed(transform)
                painter.drawPixmap(x - frame.width(), y, flipped)
