"""Gefälschte Endungen, Bildbomben und Metadaten dürfen nicht in den Speicher gelangen."""

from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin

from app.data.files.images import ImageProcessor


def encoded(format="PNG", size=(80, 40)):
    stream = BytesIO()
    image = Image.new("RGB", size, "orange")
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "private metadata")
    image.save(stream, format=format, pnginfo=metadata)
    return stream.getvalue()


@pytest.mark.parametrize("format", ["JPEG", "PNG", "WEBP"])
def test_supported_images_are_reencoded_without_metadata(format):
    original, thumbnail, width, height = ImageProcessor().prepare(encoded(format))
    assert (width, height) == (80, 40)
    for content in (original, thumbnail):
        with Image.open(BytesIO(content)) as decoded:
            assert decoded.format == "WEBP"
            assert not decoded.getexif()
            assert "Comment" not in decoded.info
    assert b"private metadata" not in original


@pytest.mark.parametrize(
    "content",
    [b"<svg onload='alert(1)'/>", b"%PDF-1.7", b"", encoded()[:30], b"<script>alert(1)</script>"],
)
def test_non_images_and_truncated_images_are_rejected(content):
    with pytest.raises(ValueError):
        ImageProcessor().prepare(content)


def test_pixel_limit_checked_before_decompression(monkeypatch):
    monkeypatch.setattr("app.data.files.images.MAX_PIXELS", 3000)
    with pytest.raises(ValueError):
        ImageProcessor().prepare(encoded())


def test_animation_rejected():
    stream = BytesIO()
    Image.new("RGB", (20, 20), "red").save(
        stream,
        format="WEBP",
        save_all=True,
        append_images=[Image.new("RGB", (20, 20), "blue")],
        duration=50,
        loop=0,
    )
    with pytest.raises(ValueError):
        ImageProcessor().prepare(stream.getvalue())


def test_thumbnail_is_bounded_and_orientation_is_applied():
    stream = BytesIO()
    image = Image.new("RGB", (900, 700), "orange")
    exif = Image.Exif()
    exif[274] = 6
    image.save(stream, format="JPEG", exif=exif)
    original, thumbnail, width, height = ImageProcessor().prepare(stream.getvalue())
    assert (width, height) == (700, 900)
    with Image.open(BytesIO(thumbnail)) as decoded:
        assert max(decoded.size) == 640
    with Image.open(BytesIO(original)) as decoded:
        assert decoded.size == (700, 900)
        assert not decoded.getexif()
