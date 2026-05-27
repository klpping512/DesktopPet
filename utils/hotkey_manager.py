"""Global hotkey manager using pynput in a daemon thread.
Uses a queue to communicate hotkey events from the listener thread
to the Qt main thread via QTimer polling.
"""
import queue
import threading
from PyQt6.QtCore import QTimer

# macOS virtual key codes (for reference, not used directly)
_KEY_CODES = {
    "S": 0x01, "W": 0x0D, "D": 0x02, "H": 0x04,
    "Z": 0x06, "X": 0x07, "P": 0x23,
}


class HotkeyManager:
    """Manages global hotkeys via pynput listener thread."""

    def __init__(self):
        self._hotkeys = {}       # {key_name: callback}
        self._event_queue = queue.Queue()
        self._listener = None
        self._poll_timer = None
        self._started = False

    def register(self, key_name: str, callback) -> bool:
        key_name = key_name.upper()
        if key_name not in _KEY_CODES:
            return False

        self._hotkeys[key_name] = callback

        if not self._started:
            self._started = True
            QTimer.singleShot(0, self._start)

        return True

    def _start(self):
        """Start the pynput listener thread and polling timer."""
        from pynput import keyboard

        pressed = set()
        event_queue = self._event_queue
        hotkey_chars = {k.lower() for k in self._hotkeys.keys()}

        def on_press(key):
            pressed.add(key)

            ctrl = (keyboard.Key.ctrl_l in pressed or
                    keyboard.Key.ctrl_r in pressed or
                    keyboard.Key.ctrl in pressed)
            shift = (keyboard.Key.shift in pressed or
                     keyboard.Key.shift_r in pressed)

            if not (ctrl and shift):
                return

            # Check if the pressed key matches a registered hotkey
            if isinstance(key, keyboard.KeyCode):
                ch = getattr(key, 'char', None)
                if ch and ch.lower() in hotkey_chars:
                    event_queue.put(ch.upper())

        def on_release(key):
            pressed.discard(key)

        self._listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release,
        )
        self._listener.daemon = True
        self._listener.start()

        # Poll the event queue on the Qt main thread
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll)
        self._poll_timer.start(50)  # Check every 50ms

    def _poll(self):
        """Check the event queue and dispatch callbacks on the Qt main thread."""
        while not self._event_queue.empty():
            try:
                key_name = self._event_queue.get_nowait()
                if key_name in self._hotkeys:
                    self._hotkeys[key_name]()
            except queue.Empty:
                break

    def unregister_all(self):
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

        if self._listener:
            self._listener.stop()
            self._listener = None

        self._hotkeys.clear()
        self._started = False


_instance = None


def get_manager() -> HotkeyManager:
    global _instance
    if _instance is None:
        _instance = HotkeyManager()
    return _instance
