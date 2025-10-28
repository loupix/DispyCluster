"""Worker image (exemple).

Fournit une fonction de redimensionnement factice. Dans un vrai cas, on
utiliserait Pillow (PIL) ou OpenCV.
"""

from typing import Optional


def resize(image_path: str, width: int, height: int) -> Optional[str]:
    """Redimensionne une image fictivement et retourne un message de succès."""
    # Placeholder de traitement image
    try:
        with open(image_path, "rb") as _:
            pass
        return f"Image redimensionnée à {width}x{height}"
    except FileNotFoundError:
        return None

