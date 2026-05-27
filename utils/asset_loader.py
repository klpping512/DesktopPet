"""Asset loader - loads sprite frames from variation directories"""
import os
import sys
from PyQt6.QtGui import QPixmap
from animation.state_machine import PetState

# Map PetState to directory names
STATE_DIR_MAP = {
    PetState.IDLE: "idle",
    PetState.MOUSE_NEAR: "near",
    PetState.FOLLOW_MOUSE: "follow",
    PetState.SLEEP: "sleep",
    PetState.WAKE_UP: "idle",       # fallback: wake uses idle frames
    PetState.CLICKED: "clicked",
    PetState.DRAGGED: "dragged",
    PetState.DROP: "drop",
    PetState.ANGRY: "angry",
    PetState.PURR: "idle",          # fallback: purr uses idle frames
    PetState.WALK: "walk",
    PetState.ALERT_SIT: "clicked",  # fallback: alert uses clicked frames
    PetState.ALERT_WATER: "idle",   # fallback: water uses idle frames
}


class AssetLoader:
    """Loads sprite frames from the assets directory"""

    def __init__(self, species: str, size: str, variation: str):
        self.species = species
        self.size = size
        self.variation = variation
        self.base_path = self._find_base_path()
        self.is_precolored = self._check_precolored()

    def _find_base_path(self) -> str:
        """Find the asset directory, checking multiple possible locations."""
        # Try in-app bundle resources first (PyInstaller)
        candidates = [
            os.path.join(os.path.dirname(__file__), "..", "assets", "sprites"),
            os.path.join(os.getcwd(), "assets", "sprites"),
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sprites"),
        ]
        # Check Resources/assets/sprites for .app bundle
        if getattr(sys, 'frozen', False):
            # Running in PyInstaller bundle
            base = os.path.dirname(sys.executable)
            candidates.insert(0, os.path.join(base, "assets", "sprites"))
            # Also check Resources directory
            resources = os.path.join(os.path.dirname(base), "Resources", "assets", "sprites")
            candidates.insert(0, resources)

        for path in candidates:
            resolved = os.path.abspath(path)
            if os.path.isdir(resolved):
                return resolved
        return candidates[0]

    def _check_precolored(self) -> bool:
        """Check if pre-colored sprites exist (skip palette shift)."""
        var_dir = os.path.join(self.base_path, self.variation)
        return os.path.isdir(var_dir)

    def get_sprites(self) -> dict:
        """Load all sprite frames, returns {PetState: [QPixmap, ...]}"""
        sprites = {}
        var_dir = os.path.join(self.base_path, self.variation)
        fallback_dir = os.path.join(self.base_path, "orange")  # fallback to orange

        for state in PetState:
            dir_name = STATE_DIR_MAP.get(state)
            if not dir_name:
                continue

            # Try variation dir first, then fallback
            state_dir = os.path.join(var_dir, dir_name)
            if not os.path.isdir(state_dir):
                state_dir = os.path.join(fallback_dir, dir_name)

            frames = self._load_frames(state_dir)
            if frames:
                sprites[state] = frames

        # Ensure at least IDLE has frames
        if PetState.IDLE not in sprites:
            fallback_idle = os.path.join(fallback_dir, "idle")
            sprites[PetState.IDLE] = self._load_frames(fallback_idle) or [QPixmap()]

        return sprites

    def _load_frames(self, directory: str) -> list:
        """Load all PNG frames from a directory, sorted by name."""
        if not os.path.isdir(directory):
            return []
        try:
            files = sorted([
                f for f in os.listdir(directory)
                if f.lower().endswith(".png")
            ])
            return [QPixmap(os.path.join(directory, f)) for f in files]
        except Exception:
            return []
