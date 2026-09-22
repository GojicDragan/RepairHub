"""Dekodieren statt Dateiendungen vertrauen; Original und Vorschau enthalten keine Metadaten."""

import warnings
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000


class ImageProcessor:
    def prepare(self, content: bytes) -> tuple[bytes, bytes, int, int]:
        if not 0 < len(content) <= MAX_BYTES:
            raise ValueError("invalid_image")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as source:
                    if (
                        source.width * source.height > MAX_PIXELS
                        or getattr(source, "n_frames", 1) != 1
                    ):
                        raise ValueError("invalid_image")
                    # verify() prüft die Dateistruktur, macht das Bild aber nicht weiter lesbar.
                    # Deshalb separat neu öffnen und load() auch die Pixel dekodieren lassen.
                    source.verify()
                with Image.open(BytesIO(content), formats=("JPEG", "PNG", "WEBP")) as source:
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    # Ein neues Pixelbild übernimmt weder GPS/EXIF noch Kommentare,
                    # angehängte Fremddaten oder sonstige Metadaten der Eingabe.
                    image = Image.new("RGBA", oriented.size)
                    image.paste(oriented.convert("RGBA"))
                    original = self.encode(image)
                    # thumbnail() verändert das Bild; die volle Auflösung ist bereits kodiert.
                    image.thumbnail((640, 640))
                    thumbnail = self.encode(image)
                    return original, thumbnail, oriented.width, oriented.height
        except (
            UnidentifiedImageError,
            OSError,
            SyntaxError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise ValueError("invalid_image") from None

    @staticmethod
    def encode(image):
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=90, method=4)
        value = buffer.getvalue()
        if len(value) > MAX_BYTES:
            raise ValueError("invalid_image")
        return value
