"""images.py on real images: the part that keeps home locations private."""
import io

import pytest
from PIL import ExifTags, Image, ImageCms

import images
from tests.conftest import image_bytes

GPS_IFD = ExifTags.IFD.GPSInfo


def exif_with_gps(orientation=1):
    exif = Image.Exif()
    exif[ExifTags.Base.Make] = "PhoneMaker"
    exif[ExifTags.Base.DateTimeOriginal] = "2026:12:24 18:00:00"
    exif[ExifTags.Base.Orientation] = orientation
    exif.get_ifd(GPS_IFD).update({
        ExifTags.GPS.GPSLatitudeRef: "N", ExifTags.GPS.GPSLatitude: (40.0, 44.0, 54.36),
        ExifTags.GPS.GPSLongitudeRef: "W", ExifTags.GPS.GPSLongitude: (73.0, 59.0, 8.36),
    })
    return exif.tobytes()


XMP_WITH_GPS = (
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description xmlns:exif="http://ns.adobe.com/exif/1.0/" exif:GPSLatitude="40,44.906N" '
    b'exif:GPSLongitude="73,59.139W"/></rdf:RDF></x:xmpmeta>'
)


def opened(data):
    image = Image.open(io.BytesIO(data))
    image.load()
    return image


def assert_no_location(data):
    image = opened(data)
    assert image.format == "WEBP"
    assert "exif" not in image.info and "xmp" not in image.info
    assert len(image.getexif()) == 0
    assert b"GPS" not in data and b"PhoneMaker" not in data and b"40,44" not in data


def test_photo_variants_strip_exif_gps_and_camera_details():
    original = image_bytes(exif=exif_with_gps())
    assert b"PhoneMaker" in original  # the fixture really carries EXIF
    for output in images.photo_variants(original):
        assert_no_location(output)


def test_photo_variants_strip_xmp_location():
    original = image_bytes(xmp=XMP_WITH_GPS)
    assert b"40,44.906N" in original
    for output in images.photo_variants(original):
        assert_no_location(output)


def test_avatar_strips_location_too():
    assert_no_location(images.avatar(image_bytes(exif=exif_with_gps(), xmp=XMP_WITH_GPS)))


def test_rotation_from_exif_is_applied_before_stripping():
    # Orientation 6 = the camera was turned; the stored 800x600 pixels display as 600x800
    display, thumb = images.photo_variants(image_bytes((800, 600), exif=exif_with_gps(orientation=6)))
    assert opened(display).size == (600, 800)
    assert opened(thumb).size == (300, 400)


def test_sizes_cap_the_long_side_and_never_enlarge():
    display, thumb = images.photo_variants(image_bytes((4032, 3024)))
    assert opened(display).size == (1600, 1200)
    assert opened(thumb).size == (400, 300)
    small_display, small_thumb = images.photo_variants(image_bytes((300, 200)))
    assert opened(small_display).size == (300, 200) and opened(small_thumb).size == (300, 200)


def test_avatar_is_a_centered_512_square():
    # Left half red, right half blue, middle stripe green: a center crop keeps the green middle
    image = Image.new("RGB", (1200, 600), (255, 0, 0))
    image.paste((0, 0, 255), (600, 0, 1200, 600))
    image.paste((0, 255, 0), (500, 0, 700, 600))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    avatar = opened(images.avatar(buffer.getvalue())).convert("RGB")
    assert avatar.size == (512, 512)
    r, g, b = avatar.getpixel((256, 256))
    assert g > 200 and r < 60 and b < 60


def test_transparency_is_kept_for_pngs_and_dropped_for_jpegs():
    display, _ = images.photo_variants(image_bytes(mode="RGBA", format="PNG"))
    assert opened(display).mode == "RGBA"
    display, _ = images.photo_variants(image_bytes())
    assert opened(display).mode == "RGB"


def test_color_profile_is_kept():
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    display, _ = images.photo_variants(image_bytes(icc_profile=profile))
    assert opened(display).info.get("icc_profile") == profile


def test_heic_photos_are_supported():
    import pillow_heif
    if not pillow_heif.libheif_info().get("HEIF"):
        pytest.skip("this libheif build can't write HEIC test files")
    display, _ = images.photo_variants(image_bytes((640, 480), format="HEIF"))
    assert opened(display).size == (640, 480)


@pytest.mark.parametrize("data", [
    b"",
    b"not an image at all",
    b"<html><script>alert(1)</script></html>",  # e.g. a renamed .jpg
    image_bytes()[:200],  # truncated
])
def test_unreadable_files_are_rejected(data):
    with pytest.raises(images.InvalidImage):
        images.photo_variants(data)
    with pytest.raises(images.InvalidImage):
        images.avatar(data)


def test_decompression_bombs_are_rejected(monkeypatch):
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)  # 2x this raises
    with pytest.raises(images.InvalidImage):
        images.photo_variants(image_bytes((100, 100)))


def test_large_phone_photos_are_allowed():
    # A 48-megapixel photo is under the limit
    assert Image.MAX_IMAGE_PIXELS >= 8064 * 6048
