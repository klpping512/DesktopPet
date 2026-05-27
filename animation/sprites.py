"""Sprite renderer - manages frame timing and state-based animation"""
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QPoint
from animation.state_machine import PetState


class SpriteRenderer:
    """Handles frame cycling per state, scale, and blending"""

    def __init__(self, sprites: dict):
        self.sprites = sprites  # {PetState: [QPixmap, ...]}
        self.scale = 1.0
        self._frame_index = 0
        self._frame_timer = 0.0
        self._current_state = PetState.IDLE

        # Frame timing (seconds per frame)
        self.frame_times = {
            PetState.IDLE: 0.25,  # 4 fps
            PetState.MOUSE_NEAR: 0.2,  # 5 fps
            PetState.FOLLOW_MOUSE: 0.125,  # 8 fps
            PetState.SLEEP: 0.5,  # 2 fps
            PetState.WAKE_UP: 0.15,  # ~7 fps
            PetState.CLICKED: 0.1,  # 10 fps
            PetState.DRAGGED: 0.167,  # 6 fps
            PetState.DROP: 0.1,  # 10 fps
            PetState.ALERT_SIT: 0.15,  # ~7 fps
            PetState.ALERT_WATER: 0.15,  # ~7 fps
            PetState.ANGRY: 0.12,  # ~8 fps — attack animation
            PetState.PURR: 0.3,  # ~3 fps — slow relaxed
            PetState.WALK: 0.15,  # ~7 fps — walking
        }

        # Which states loop
        self.looping_states = {
            PetState.IDLE, PetState.MOUSE_NEAR, PetState.FOLLOW_MOUSE,
            PetState.SLEEP, PetState.DRAGGED, PetState.WALK,
        }

        # Which states auto-transition after one cycle
        self.auto_next = {
            PetState.WAKE_UP: PetState.IDLE,
            PetState.CLICKED: PetState.IDLE,
            PetState.DROP: PetState.IDLE,
            PetState.ALERT_SIT: PetState.IDLE,
            PetState.ALERT_WATER: PetState.IDLE,
            PetState.ANGRY: PetState.IDLE,
            PetState.PURR: PetState.IDLE,
        }

    def set_scale(self, s: float):
        self.scale = s

    def update(self, state: PetState, dt: float):
        """Advance animation by dt seconds"""
        # State change → reset frame
        if state != self._current_state:
            self._current_state = state
            self._frame_index = 0
            self._frame_timer = 0.0
            return

        frames = self.sprites.get(state, [])
        if not frames:
            return

        fps = self.frame_times.get(state, 0.2)
        self._frame_timer += dt

        if self._frame_timer >= fps:
            self._frame_timer = 0
            self._frame_index += 1

            # Looping → wrap around
            if state in self.looping_states:
                self._frame_index %= max(len(frames), 1)
            # Non-looping → hold last frame
            elif self._frame_index >= len(frames):
                self._frame_index = len(frames) - 1

    def get_current_frame(self) -> QPixmap:
        """Get current animation frame as QPixmap"""
        frames = self.sprites.get(self._current_state, [])
        if not frames:
            return QPixmap()

        idx = min(self._frame_index, len(frames) - 1)
        frame = frames[idx]

        if self.scale != 1.0:
            new_w = int(frame.width() * self.scale)
            new_h = int(frame.height() * self.scale)
            if new_w > 0 and new_h > 0:
                frame = frame.scaled(new_w, new_h)

        return frame

    @property
    def animation_complete(self) -> bool:
        """Has current non-looping animation finished?"""
        if self._current_state in self.looping_states:
            return False
        frames = self.sprites.get(self._current_state, [])
        return self._frame_index >= len(frames) - 1
