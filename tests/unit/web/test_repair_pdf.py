"""Vollständigkeit, Umbrüche, Markup-Abwehr und unveränderte Domain-Kosten im PDF."""

from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

from pypdf import PdfReader

from app.domains.devices.dto import Device
from app.domains.repairs.dto import PartPosition, Repair, RepairDetails, Step
from app.web.documents.repair_pdf import render_repair_pdf


def sample(count=1):
    return RepairDetails(
        Repair(
            42,
            3,
            "Radio Küche",
            "Fault <b>not markup</b> & safe\nSecond line",
            "open",
            datetime(2026, 9, 22, tzinfo=UTC),
        ),
        tuple(
            Step(i, 42, f"Step {i}: " + "Long repair description " * 40, i % 2 == 0)
            for i in range(count)
        ),
        count,
        0,
        hours=Decimal("1.25"),
        hourly_rate=Decimal("80.00"),
        parts=tuple(
            PartPosition(
                i, f"Part {i} <img src='https://invalid.test'>", Decimal("3.33"), 3, Decimal("9.99")
            )
            for i in range(count)
        ),
        part_total=count,
        labor_cost=Decimal("100.00"),
        parts_cost=Decimal("9.99"),
        total_cost=Decimal("109.99"),
    )


def test_report_is_multipage_complete_and_inert(tmp_path):
    content = render_repair_pdf(sample(25), Device(3, "Radio Küche", "Müller", "R-ä"), lambda x: x)
    reader = PdfReader(BytesIO(content))
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert len(reader.pages) > 2
    for expected in (
        "Radio Küche",
        "Müller",
        "Step 24",
        "Part 24",
        "CHF 109.99",
        "<b>not markup</b>",
    ):
        assert expected in text
    assert not any(page.get("/Annots") for page in reader.pages)
    assert all("RepairHub" in page.extract_text() for page in reader.pages)
    assert reader.metadata.title == "Repair report #42"


def test_empty_report_and_long_fault_split_without_truncation():
    from dataclasses import replace

    data = sample(0)
    data = replace(data, repair=replace(data.repair, description="word " * 1900 + "END-FAULT"))
    reader = PdfReader(
        BytesIO(render_repair_pdf(data, Device(3, "Radio", "Acme", "R"), lambda x: x))
    )
    text = "\n".join(p.extract_text() for p in reader.pages)
    assert "END-FAULT" in text
    assert "No parts recorded." in text
    assert "No repair steps recorded." in text
