"""Color palette - applies HSV shifts to recolor sprites"""
from PyQt6.QtGui import QPixmap, QImage, QColor


# Target colors for primary hues (H, S, V ranges)
COLOR_MAPS = {
    "orange": {
        "hue": 20, "sat": 0.8, "bri": 0.9,
    },
    "black": {
        "hue": 0, "sat": 0.2, "bri": 0.45,
    },
    "white": {
        "hue": 0, "sat": 0.1, "bri": 0.9,
    },
    "brown": {
        "hue": 25, "sat": 0.7, "bri": 0.5,
    },
    "grey": {
        "hue": 0, "sat": 0.1, "bri": 0.55,
    },
    "cream": {
        "hue": 40, "sat": 0.4, "bri": 0.95,
    },
    "red": {
        "hue": 0, "sat": 0.85, "bri": 0.85,
    },
    "chocolate": {
        "hue": 20, "sat": 0.7, "bri": 0.35,
    },
    "blue_solid": {
        "hue": 210, "sat": 0.5, "bri": 0.6,
    },
}


def apply_color_palette(sprites: dict, primary: str, secondary: str = None) -> dict:
    """Apply color palette to all sprite frames.
    Uses sprite luminance to preserve shading while shifting hue.
    """
    target = COLOR_MAPS.get(primary, COLOR_MAPS["orange"])
    secondary_target = COLOR_MAPS.get(secondary) if secondary else None

    result = {}
    for state, frames in sprites.items():
        recolored = []
        for frame in frames:
            recolored.append(_recolor_pixmap(frame, target, secondary_target))
        result[state] = recolored
    return result


def _recolor_pixmap(pixmap: QPixmap, target: dict, secondary: dict = None) -> QPixmap:
    """Recolor a pixmap by shifting hue toward target while preserving luminance."""
    if pixmap.isNull():
        return pixmap

    image = pixmap.toImage()
    width = image.width()
    height = image.height()

    for y in range(height):
        for x in range(width):
            color = QColor(image.pixel(x, y))
            if color.alpha() < 10:
                continue

            h, s, v, a = color.hue(), color.saturation(), color.value(), color.alpha()

            # Use secondary target for bright pixels (highlights)
            t = secondary if secondary and v > 200 else target

            # Preserve original luminance gradient but shift hue/saturation
            h = t["hue"]
            new_s = max(0, min(255, int(s * t["sat"])))
            new_v = max(0, min(255, int(v * t["bri"])))

            shifted = QColor.fromHsv(h if h >= 0 else 0, new_s, new_v, a)
            image.setPixel(x, y, shifted.rgba())

    return QPixmap.fromImage(image)
