"""PDF-Präsentation ohne Datenzugriff oder eigene Kostenformeln.

Platypus übernimmt Umbrüche und wiederholte Tabellenköpfe:
https://docs.reportlab.com/reportlab/userguide/ch5_platypus/
"""

from datetime import UTC, datetime
from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Mit ReportLab gelieferte, lizenzierte Schrift einbetten; keine System-/Netzwerkfonts.
_fonts = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("RepairHub", str(_fonts / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("RepairHubBold", str(_fonts / "VeraBd.ttf")))
INK = colors.HexColor("#243b35")
ACCENT = colors.HexColor("#b84020")
PAPER = colors.HexColor("#f8f6f0")
LINE = colors.HexColor("#d9dcd1")


def render_repair_pdf(data, device, translate, *, generated_at=None):
    # Übersetzung und Uhrzeit sind übergebbar; Dokumenttests benötigen keinen Flask-Kontext.
    _ = translate
    generated_at = generated_at or datetime.now(UTC)
    output = BytesIO()
    title = _("Repair report")
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=34 * mm,
        bottomMargin=23 * mm,
        title=f"{title} #{data.repair.id}",
        author="RepairHub",
    )
    body = ParagraphStyle(
        "body",
        fontName="RepairHub",
        fontSize=9,
        leading=14,
        textColor=INK,
        spaceAfter=7,
        splitLongWords=True,
    )
    heading = ParagraphStyle(
        "heading",
        parent=body,
        fontName="RepairHubBold",
        fontSize=13,
        leading=18,
        spaceBefore=15,
        spaceAfter=9,
        keepWithNext=True,
    )
    hero = ParagraphStyle("hero", parent=heading, fontSize=24, leading=30, spaceBefore=0)
    # Das kurze Schrittlabel darf nicht allein am unteren Seitenrand stehen bleiben.
    step_label = ParagraphStyle("step", parent=body, keepWithNext=True)
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)

    def paragraph(value, style=body):
        # Benutzertexte sind nur Text: keine ReportLab-Markup-Tags, Bilder oder Links zulassen.
        text = "".join(c for c in str(value) if c in "\n\t" or ord(c) >= 32)
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    def money(value):
        # Bereits von der Domäne gerundet; keine abweichende PDF-Kostenberechnung.
        return f"CHF {value:.2f}"

    statuses = {"open": _("Open"), "in_progress": _("In progress"), "completed": _("Completed")}
    story = [
        paragraph(title, hero),
        paragraph(f"#{data.repair.id} · {statuses[data.repair.status]}"),
        paragraph(_("Generated") + ": " + generated_at.strftime("%Y-%m-%d %H:%M UTC")),
        paragraph(_("Device"), heading),
        paragraph(device.name),
        paragraph(_("Manufacturer") + ": " + device.manufacturer),
        paragraph(_("Model") + ": " + device.model),
        paragraph(_("Created") + ": " + data.repair.created_at.strftime("%Y-%m-%d %H:%M UTC")),
        paragraph(_("Fault description"), heading),
        paragraph(data.repair.description),
        paragraph(_("Repair steps"), heading),
    ]
    if not data.steps:
        story.append(paragraph(_("No repair steps recorded.")))
    for index, step in enumerate(data.steps, 1):
        story.append(
            paragraph(f"{index}. {_('Done') if step.completed else _('Pending')}", step_label)
        )
        story.append(paragraph(step.description))
    story.append(paragraph(_("Parts"), heading))
    if data.parts:
        rows = [
            [paragraph(label) for label in (_("Part"), _("Quantity"), _("Unit price"), _("Total"))]
        ]
        rows.extend(
            [
                [
                    paragraph(p.name),
                    paragraph(p.quantity, right),
                    paragraph(money(p.unit_price), right),
                    paragraph(money(p.total), right),
                ]
                for p in data.parts
            ]
        )
        # Kopf auf Folgeseiten wiederholen; auch sehr hohe Textzeilen dürfen umbrechen.
        table = LongTable(
            rows,
            colWidths=[75 * mm, 20 * mm, 37 * mm, 38 * mm],
            repeatRows=1,
            splitByRow=1,
            splitInRow=1,
            hAlign="LEFT",
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PAPER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.6, ACCENT),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINE),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
    else:
        story.append(paragraph(_("No parts recorded.")))
    story.extend(
        [
            paragraph(_("Estimated costs"), heading),
            paragraph(_("Working hours") + f": {data.hours:.2f}"),
            paragraph(_("Hourly rate") + ": " + money(data.hourly_rate)),
        ]
    )
    totals = Table(
        [
            [paragraph(label), paragraph(money(value), right)]
            for label, value in [
                (_("Labour cost"), data.labor_cost),
                (_("Parts cost"), data.parts_cost),
                (_("Estimated total"), data.total_cost),
            ]
        ],
        colWidths=[110 * mm, 60 * mm],
    )
    totals.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, -1), (-1, -1), PAPER),
                ("LINEABOVE", (0, -1), (-1, -1), 1, ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.extend(
        [
            totals,
            Spacer(1, 8 * mm),
            paragraph(_("Cost estimate only. This report is not an invoice.")),
        ]
    )

    def page(canvas, doc):
        # Seitenrahmen dürfen Schrift/Farbe der anschliessenden Inhalte nicht verändern.
        canvas.saveState()
        canvas.setFillColor(INK)
        canvas.rect(0, A4[1] - 22 * mm, A4[0], 22 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("RepairHubBold", 17)
        canvas.drawString(20 * mm, A4[1] - 14 * mm, "RepairHub")
        canvas.setStrokeColor(ACCENT)
        canvas.line(20 * mm, 18 * mm, 190 * mm, 18 * mm)
        canvas.setFillColor(INK)
        canvas.setFont("RepairHub", 8)
        canvas.drawString(20 * mm, 12 * mm, f"{title} #{data.repair.id}")
        canvas.drawRightString(190 * mm, 12 * mm, _("Page") + f" {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=page, onLaterPages=page)
    return output.getvalue()
