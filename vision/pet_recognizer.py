"""Pet analyzer - local color classification using PIL"""
import os
from PIL import Image

# Color buckets for pixel classification (hue range, saturation range, brightness range)
COLOR_RANGES = {
    "orange": ((15, 40), (80, 255), (100, 255)),
    "black": ((0, 360), (0, 80), (0, 60)),
    "white": ((0, 360), (0, 40), (180, 255)),
    "brown": ((10, 35), (80, 255), (60, 150)),
    "grey": ((0, 360), (0, 40), (60, 180)),
    "cream": ((20, 55), (30, 120), (140, 255)),
    "red": ((0, 10), (150, 255), (120, 255)),
    "chocolate": ((10, 30), (100, 255), (30, 80)),
}

# "Warm" color names — aggregated for calico/tortie detection
WARM_COLORS = {"orange", "brown", "cream", "red", "chocolate"}


class PetAnalyzer:
    """Analyzes pet photos to determine species, size, colors, and pattern."""

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.image = Image.open(image_path).convert("RGB")

    def analyze(self) -> dict:
        """Run full analysis pipeline."""
        result = {"species": "cat", "size_group": "medium"}

        colors = self._analyze_colors()
        result.update(colors)

        pattern = self._detect_pattern(result)
        result["pattern"] = pattern

        return result

    def _analyze_colors(self) -> dict:
        """Classify pixels into color buckets with warm-light compensation."""
        img = self.image.copy()
        img.thumbnail((200, 200))
        pixels = list(img.getdata())

        counts = {c: 0 for c in COLOR_RANGES}
        total = len(pixels)

        for r, g, b in pixels:
            mx, mn = max(r, g, b), min(r, g, b)

            # Early warm-white detection: near-white under warm light
            # e.g. (230, 215, 200) — white fur with warm lighting
            if mn > 150 and mx > 200 and (mx - mn) < 60:
                counts["white"] += 1
                continue

            # Early warm-black detection: near-black under warm light
            if mx < 80 and (mx - mn) < 30:
                counts["black"] += 1
                continue

            # Broad neutral → white/grey (not colored)
            if mx - mn < 40:
                avg = (r + g + b) / 3
                if avg > 150:
                    counts["white"] += 1
                elif avg > 100:
                    # Split between grey and white
                    if avg > 130:
                        counts["white"] += 1
                    else:
                        counts["grey"] += 1
                else:
                    counts["black"] += 1
                continue

            # Hue-based classification
            hue = self._rgb_to_hue(r, g, b)
            sat = (mx - mn) / max(mx, 1)
            bri = mx

            if bri < 60:
                counts["black"] += 1
            elif sat < 0.15 and bri > 150:
                counts["white"] += 1
            elif sat < 0.2:
                if bri > 150:
                    counts["white"] += 1
                elif bri > 100:
                    counts["grey"] += 1
                else:
                    counts["black"] += 1
            else:
                matched = False
                for name, (h_range, s_range, b_range) in COLOR_RANGES.items():
                    if name in ("black", "white", "grey"):
                        continue
                    h_min, h_max = h_range
                    s_min, s_max = s_range
                    b_min, b_max = b_range
                    if h_min <= hue <= h_max and s_min <= sat * 255 <= s_max and b_min <= bri <= b_max:
                        counts[name] += 1
                        matched = True
                        break
                if not matched:
                    if bri < 100:
                        counts["black"] += 1
                    else:
                        counts["grey"] += 1

        # Determine primary and secondary colors
        sorted_colors = sorted(counts.items(), key=lambda x: -x[1])
        primary = sorted_colors[0][0]
        primary_pct = sorted_colors[0][1] / total * 100
        secondary = sorted_colors[1][0] if sorted_colors[1][1] / total > 0.15 else None

        # Black+white combined > 55% → override primary (but check for warm colors first)
        black_pct = counts["black"] / total * 100
        white_pct = counts["white"] / total * 100
        warm_pct = sum(counts[w] for w in WARM_COLORS) / total * 100

        # Calico/tortie guard: if there's significant warm color, don't override to bicolor
        if warm_pct > 8:
            pass  # Keep primary from sorted colors, pattern detection handles calico/tortie
        elif black_pct + white_pct > 55:
            if black_pct >= white_pct:
                primary = "black"
                secondary = "white" if white_pct > 15 else None
            else:
                primary = "white"
                secondary = "black" if black_pct > 15 else None

        # Grey dominant with black secondary → treat as black+white
        grey_pct = counts["grey"] / total * 100
        if primary == "grey" and grey_pct + black_pct > 20:
            primary = "black"
            secondary = "white"

        return {
            "primary_color": primary,
            "secondary_color": secondary,
            "color_counts": counts,
            "total_pixels": total,
        }

    def _rgb_to_hue(self, r, g, b) -> float:
        """Convert RGB to hue angle (0-360)."""
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == mn:
            return 0
        d = mx - mn
        if mx == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        return h * 60

    def _detect_pattern(self, color_result: dict) -> str:
        """Detect coat pattern based on color distribution."""
        counts = color_result.get("color_counts", {})
        total = color_result.get("total_pixels", 1)
        primary = color_result.get("primary_color")
        secondary = color_result.get("secondary_color")

        white_pct = counts.get("white", 0) / total * 100
        black_pct = counts.get("black", 0) / total * 100
        grey_pct = counts.get("grey", 0) / total * 100
        orange_pct = counts.get("orange", 0) / total * 100
        warm_pct = sum(counts.get(w, 0) for w in WARM_COLORS) / total * 100
        dark_pct = black_pct + grey_pct

        # Calico: warm + dark + white (tri-color)
        if warm_pct > 8 and dark_pct > 10 and white_pct > 15:
            return "calico"

        # Tortie: warm + dark, low white (bi-color marbled)
        if warm_pct > 8 and dark_pct > 10:
            return "tortie"

        # Has white + another significant color → bicolor
        if white_pct > 20 and secondary:
            if primary in ("black", "grey") and secondary == "white":
                return "bicolor"
            if primary == "white" and secondary in ("black", "grey", "orange"):
                return "bicolor"

        # Has orange + black → calico/tortie (direct check)
        if orange_pct > 10 and black_pct > 10:
            if white_pct > 20:
                return "calico"
            return "tortie"

        # Grey+bicolor pattern
        if grey_pct > 15 and primary == "black" and secondary == "white":
            return "bicolor"

        return "solid"

    @staticmethod
    def resolve_variation(pet_data: dict) -> str:
        """Determine the sprite variation name from analysis results."""
        primary = pet_data.get("primary_color", "orange")
        secondary = pet_data.get("secondary_color")
        pattern = pet_data.get("pattern", "solid")

        # Pattern-based mapping
        if pattern == "bicolor":
            if primary in ("black", "grey"):
                return "black_bicolor"
            if primary == "white" and secondary in ("black", "grey"):
                return "black_bicolor"
            return "black_bicolor"  # default bicolor

        if pattern == "calico":
            return "calico"

        if pattern == "tortie":
            return "tortie"

        # Solid colors
        solid_map = {
            "orange": "orange",
            "black": "black",
            "white": "white",
            "brown": "brown",
            "grey": "grey",
            "cream": "cream",
            "red": "red",
            "chocolate": "chocolate",
        }

        if primary == "blue_solid":
            return "blue_solid"

        # Tabby detection via secondary colors
        if secondary and primary in ("orange", "brown", "grey"):
            return "tabby_mackerel"

        return solid_map.get(primary, "orange")
