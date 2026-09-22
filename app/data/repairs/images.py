from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.data.files.model import ImageColumns
from app.data.files.repository import ImagesRepository
from app.data.queries.ownership import owned_repairs
from app.data.repairs.model import Repair
from app.domains.repairs.dto import Image, ImagePage
from app.extensions import db


class RepairImage(ImageColumns, db.Model):
    __tablename__ = "repairs_images"
    __table_args__ = (
        CheckConstraint(
            "width > 0 AND height > 0 AND width::bigint * height <= 20000000",
            name="ck_repairs_images_dimensions",
        ),
        CheckConstraint("id ~ '^[a-f0-9]{32}$'", name="ck_repairs_images_id"),
        CheckConstraint("length(trim(filename)) > 0", name="ck_repairs_images_filename"),
        Index("ix_repairs_images_parent_id_id", "parent_id", "id"),
    )
    parent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("repairs.id"), nullable=False)


class ImageRepository(ImagesRepository):
    parent_model = Repair

    def __init__(self):
        super().__init__(RepairImage, owned_repairs, Image, ImagePage)
