
"""Utilities for extracting colours from desktop wallpapers."""

from pathlib import Path

from PIL import Image

DEFAULT_ACCENT = "#8fe3c0"
SAMPLE_SIZE = (128, 128)
PALETTE_SIZE = 8


def extract_dominant_color(
    image_path: str | Path,
    fallback: str = DEFAULT_ACCENT,
) -> str:
    """Return the most common colour in an image as a hex string.

    The image is reduced to a small sample and an eight-colour
    palette to make analysis inexpensive.

    If the image cannot be read, return the supplied fallback.
    """

    try:
        with Image.open(image_path) as original:
            original.thumbnail(SAMPLE_SIZE)
            image = original.convert("RGB")
            quantized = image.quantize(colors=PALETTE_SIZE)

            color_counts = quantized.getcolors()

            if not color_counts:
                return fallback

            # Each entry contains (pixel_count, palette_index).
            _, dominant_index = max(color_counts)

            palette = quantized.getpalette()

            if palette is None:
                return fallback

            start = dominant_index * 3
            red, green, blue = palette[start : start + 3]

            return f"#{red:02x}{green:02x}{blue:02x}"

    except (OSError, ValueError):
        return fallback
