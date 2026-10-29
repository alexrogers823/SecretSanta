"""Image processing shared by process_photo (F6) and process_profile_picture (F7).

Every output is re-encoded from pixels only: EXIF (GPS location, camera, timestamps) and XMP,
which phones can also use for location, are dropped. The color profile is kept so photos from
wide-gamut phone cameras don't look washed out.
"""
import io

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()  # iPhone HEIC photos

# Refuse "decompression bombs": a 48-megapixel phone photo is ~49M pixels
Image.MAX_IMAGE_PIXELS = 60_000_000

DISPLAY_MAX_SIDE = 1600
THUMB_MAX_SIDE = 400
AVATAR_SIDE = 512
WEBP_QUALITY = 82


class InvalidImage(Exception):
    pass


def _open(raw):
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()  # decode now, so corrupt or fake files fail here rather than later
        # Rotate per the EXIF orientation before the EXIF is thrown away
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
        raise InvalidImage(str(error)) from error

    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    icc_profile = image.info.get("icc_profile")
    clean = image.convert("RGBA" if has_alpha else "RGB")
    clean.info = {"icc_profile": icc_profile} if icc_profile else {}
    return clean


def _webp(image):
    buffer = io.BytesIO()
    image.save(
        buffer, "WEBP", quality=WEBP_QUALITY, method=4,
        exif=b"", xmp=b"", icc_profile=image.info.get("icc_profile"),
    )
    return buffer.getvalue()


def _shrunk(image, max_side):
    copy = image.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)  # never enlarges
    return copy


def photo_variants(raw):
    """Returns (display_webp, thumb_webp): at most 1600 px and 400 px on the long side."""
    image = _open(raw)
    return _webp(_shrunk(image, DISPLAY_MAX_SIDE)), _webp(_shrunk(image, THUMB_MAX_SIDE))


def avatar(raw):
    """Returns a 512 px square WebP, center-cropped."""
    image = _open(raw)
    return _webp(ImageOps.fit(image, (AVATAR_SIDE, AVATAR_SIDE), Image.Resampling.LANCZOS))
