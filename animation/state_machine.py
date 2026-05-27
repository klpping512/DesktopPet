"""Pet state machine - manages transitions between animation states"""
import time
from enum import Enum


class PetState(Enum):
    IDLE = "idle"
    MOUSE_NEAR = "mouse_near"
    FOLLOW_MOUSE = "follow_mouse"
    SLEEP = "sleep"
    WAKE_UP = "wake_up"
    CLICKED = "clicked"
    DRAGGED = "dragged"
    DROP = "drop"
    ANGRY = "angry"
    PURR = "purr"
    WALK = "walk"
    SIT = "sit"
    PLAY = "play"
    ALERT_SIT = "alert_sit"
    ALERT_WATER = "alert_water"


# Transition rules: {from_state: [to_state1, to_state2, ...]}
# None means "any state can transition to this"
TRANSITION_RULES = {
    PetState.IDLE: [PetState.MOUSE_NEAR, PetState.SLEEP, PetState.CLICKED,
                    PetState.DRAGGED, PetState.ANGRY, PetState.WALK,
                    PetState.SIT, PetState.PLAY, PetState.ALERT_SIT,
                    PetState.ALERT_WATER, PetState.PURR],
    PetState.MOUSE_NEAR: [PetState.IDLE, PetState.FOLLOW_MOUSE, PetState.PURR,
                          PetState.CLICKED, PetState.DRAGGED, PetState.ANGRY,
                          PetState.SLEEP, PetState.WALK, PetState.SIT,
                          PetState.PLAY, PetState.ALERT_SIT, PetState.ALERT_WATER],
    PetState.FOLLOW_MOUSE: [PetState.IDLE, PetState.MOUSE_NEAR, PetState.CLICKED,
                            PetState.DRAGGED, PetState.ANGRY, PetState.PURR],
    PetState.SLEEP: [PetState.WAKE_UP],
    PetState.WAKE_UP: [PetState.IDLE],
    PetState.CLICKED: [PetState.IDLE, PetState.DRAGGED, PetState.ANGRY],
    PetState.DRAGGED: [PetState.DROP, PetState.IDLE, PetState.ANGRY],
    PetState.DROP: [PetState.IDLE],
    PetState.ANGRY: [PetState.IDLE],
    PetState.PURR: [PetState.IDLE, PetState.MOUSE_NEAR, PetState.SLEEP],
    PetState.WALK: [PetState.IDLE, PetState.MOUSE_NEAR, PetState.SLEEP,
                    PetState.CLICKED, PetState.DRAGGED, PetState.ANGRY],
    PetState.SIT: [PetState.IDLE, PetState.MOUSE_NEAR, PetState.SLEEP],
    PetState.PLAY: [PetState.IDLE, PetState.MOUSE_NEAR],
    PetState.ALERT_SIT: [PetState.IDLE],
    PetState.ALERT_WATER: [PetState.IDLE],
}

# Lock times (seconds) - state change locks machine for this duration
LOCK_TIMES = {
    PetState.ANGRY: 3.0,
    PetState.ALERT_SIT: 2.0,
    PetState.ALERT_WATER: 2.0,
}


class StateMachine:
    """Manages pet animation states and valid transitions"""

    def __init__(self):
        self.current = PetState.IDLE
        self.facing_right = True
        self._lock_until = 0.0

    def transition(self, new_state: PetState) -> bool:
        """Attempt to transition to new_state. Returns True if transitioned."""
        now = time.time()

        # Check lock
        if now < self._lock_until and new_state != self.current:
            return False

        # Allow any transition if no rules defined
        if self.current not in TRANSITION_RULES:
            self._do_transition(new_state)
            return True

        # Check if transition is valid
        allowed = TRANSITION_RULES.get(self.current, [])
        if new_state in allowed:
            self._do_transition(new_state)
            return True

        return False

    def _do_transition(self, new_state: PetState):
        self.current = new_state
        lock = LOCK_TIMES.get(new_state, 0)
        if lock > 0:
            self._lock_until = time.time() + lock

    def force(self, new_state: PetState):
        """Force transition regardless of rules and lock."""
        self._lock_until = 0
        self._do_transition(new_state)
