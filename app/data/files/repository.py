from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


class ImagesRepository:
    def __init__(self, model, owned_parent, image_type, page_type):
        self.model, self.owned_parent = model, owned_parent
        self.image_type, self.page_type = image_type, page_type

    def owns(self, owner_id, parent_id):
        return db.session.scalar(
            select(self.owned_parent(owner_id).where(self.parent_model.id == parent_id).exists())
        )

    def query(self, owner_id, parent_id):
        # Die Bild-ID allein beweist kein Eigentum: jede Abfrage bindet den
        # übergeordneten Gegenstand an den vertrauenswürdig ermittelten Benutzer.
        parents = self.owned_parent(owner_id).subquery()
        return (
            select(self.model)
            .join(parents, self.model.parent_id == parents.c.id)
            .where(self.model.parent_id == parent_id)
        )

    def dto(self, row):
        return self.image_type(row.id, row.filename, row.width, row.height)

    def add(self, owner_id, parent_id, image):
        try:
            # Eigentum nochmals unter Sperre prüfen, bevor der Verweis sichtbar wird.
            parent = db.session.scalar(
                self.owned_parent(owner_id)
                .where(self.parent_model.id == parent_id)
                .with_for_update(of=self.parent_model)
            )
            if parent is None:
                raise OSError("image_owner_changed")
            db.session.add(
                self.model(
                    id=image.id,
                    parent_id=parent_id,
                    filename=image.filename,
                    width=image.width,
                    height=image.height,
                )
            )
            db.session.commit()
        except (SQLAlchemyError, OSError):
            db.session.rollback()
            raise OSError("image_save_failed") from None

    def list(self, owner_id, parent_id, offset, limit):
        query = self.query(owner_id, parent_id)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        # Die ID entscheidet bei identischen Zeitstempeln und hält die Reihenfolge eindeutig.
        rows = db.session.scalars(
            query.order_by(self.model.created_at.desc(), self.model.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return self.page_type(tuple(self.dto(row) for row in rows), total, offset)

    def get(self, owner_id, parent_id, image_id):
        row = db.session.scalar(self.query(owner_id, parent_id).where(self.model.id == image_id))
        return self.dto(row) if row is not None else None

    def delete(self, owner_id, parent_id, image_id):
        try:
            row = db.session.scalar(
                self.query(owner_id, parent_id)
                .where(self.model.id == image_id)
                .with_for_update(of=self.model)
            )
            if row is None:
                db.session.rollback()
                return False
            # Nur den erreichbaren Verweis entfernen. Unveränderliche Objekte bleiben
            # für laufende Datenbanksicherungen erhalten; kein unsicheres S3/DB-Doppelcommit.
            db.session.delete(row)
            db.session.commit()
            return True
        except SQLAlchemyError:
            db.session.rollback()
            raise OSError("image_delete_failed") from None
