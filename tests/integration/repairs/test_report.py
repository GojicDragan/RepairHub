"""PDF nutzt Browsersitzung, vollständige Reparaturauskunft und Eigentumsfilter."""

from io import BytesIO

from pypdf import PdfReader

from tests.integration.devices.test_devices import owner as owner
from tests.integration.repairs.test_repairs import create
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit


def text(response):
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(response.data)).pages)


def test_private_report_download_and_language(owner, identity_app):
    repair = create(owner)
    path = f"/repairs/{repair}/report.pdf"
    response = owner.get(path)
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"] == f"attachment; filename=repair-{repair}.pdf"
    assert "no-store" in response.headers["Cache-Control"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Repair report" in text(response)
    assert "Reparaturbericht" in text(owner.get(path, headers={"Accept-Language": "de-CH"}))
    assert "Repair report" in text(owner.get(path, headers={"Accept-Language": "fr"}))
    assert path in owner.get(f"/repairs/{repair}").text
    foreign = identity_app.test_client()
    register(foreign, username="ReportOther", email="report-other@example.org")
    foreign.get(confirmation(identity_app))
    submit(foreign, "/login", identity="ReportOther", password=PASSWORD)
    assert foreign.get(path).status_code == 404
    assert owner.get("/repairs/999999999/report.pdf").status_code == 404
    assert identity_app.test_client().get(path).status_code == 302


def test_pdf_includes_all_pages_and_same_costs(owner, identity_app):
    from decimal import Decimal

    from app.data.parts.model import PartItem
    from app.data.repairs.model import Repair, RepairStep
    from app.extensions import db

    repair_id = create(owner)
    with identity_app.app_context():
        repair = db.session.get(Repair, repair_id)
        repair.hours, repair.hourly_rate = Decimal("1.25"), Decimal("80")
        for i in range(25):
            db.session.add(RepairStep(repair_id=repair_id, description=f"Step-{i}", completed=True))
            db.session.add(
                PartItem(
                    repair_id=repair_id, name=f"Part-{i}", unit_price=Decimal("3.33"), quantity=3
                )
            )
        db.session.commit()
    report = owner.get(f"/repairs/{repair_id}/report.pdf?offset=999&part_offset=999")
    assert report.status_code == 200
    content = text(report)
    assert "Step-24" in content and "Part-24" in content
    assert "CHF 349.75" in content
    assert "349.75" in owner.get(f"/repairs/{repair_id}").text
