import subprocess
import numpy as np
import cv2
from catprinter import logger

_MagickExe = "magick"  # or "convert" if that's your CLI name

def magick_text(text: str, image_width: int, font_size: int, font_family: str) -> bytes:
    """Render bold text using ImageMagick and return PBM bytes."""
    if _MagickExe is None:
        raise RuntimeError("ImageMagick not found")

    proc = subprocess.Popen(
        [
            _MagickExe,
            "-background", "white",
            "-fill", "black",
            "-size", f"{image_width}x",
            "-font", font_family,
            "-weight", "700",
            "-stroke", "black",
            "-strokewidth", "1",
            "-pointsize", str(font_size),
            "caption:@-",
            "pbm:-",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(input=text.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"ImageMagick failed: {err.decode('utf-8')}")
    return out


def text_to_image(text: str, width: int = 384, font_size: int = 22, font_family: str = "FreeMono") -> np.ndarray:
    """Render text via ImageMagick to a binary NumPy array."""
    logger.debug(f"⏳ Rendering text with ImageMagick: {text}")

    pbm_bytes = magick_text(text, width, font_size, font_family)
    img_array = np.frombuffer(pbm_bytes, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise RuntimeError("Failed to decode PBM image")

    logger.debug("⏳ Thresholding")
    _, binary = cv2.threshold(img, 127, 1, cv2.THRESH_BINARY_INV)
    logger.debug("✅ Done.")
    return binary
