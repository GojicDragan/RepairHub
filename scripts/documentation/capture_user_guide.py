"""Deutsche Anleitung mit Playwright an einer wegwerfbaren Instanz nachvollziehen.

Aufruf als Modul; ausschliesslich geprüfte lokale Image-Artefakte verwenden.
Die Instanz besitzt eigene Daten, SMTP-Senke und Garage; keine Produktionszugriffe.
"""

import argparse
import json
import re
import secrets
import time
from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

from scripts.ci.images import docker, verify
from scripts.ci.isolated_runtime import isolated_runtime


def run(directory, commit, output):
    manifest = verify(directory, commit)
    output.mkdir(parents=True, exist_ok=True)
    shots = []
    with isolated_runtime(manifest, publish_https=True, receive_mail=True) as runtime:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(
                base_url=runtime.public_url,
                ignore_https_errors=True,
                locale="de-CH",
                viewport={"width": 1360, "height": 1000},
            )
            context.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if route.request.url.startswith(runtime.public_url + "/")
                    else route.abort()
                ),
            )
            page = context.new_page()
            page.set_default_timeout(15000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            password = secrets.token_urlsafe(24)
            email = "anleitung@example.org"

            def shot(name, selector=None):
                # Debounce und laufende AJAX-Antworten vor der Aufnahme abschliessen.
                page.wait_for_load_state("networkidle")
                viewport = page.locator("[data-list-viewport]")
                if viewport.count():
                    expect(viewport).not_to_have_attribute("aria-busy", "true")
                page.evaluate("document.fonts.ready")
                target = page.locator(selector).first if selector else page
                # Auch kurzlebige Schlüssel und Passwörter gehören nicht in die Anleitung.
                target.screenshot(
                    path=str(output / (name + ".png")),
                    animations="disabled",
                    mask_color="#d6dfdb",
                    mask=[page.locator("#api-key-value"), page.locator("input[type=password]")],
                    **({} if selector else {"full_page": True}),
                )
                shots.append(name)
                print("Screenshot:", name, flush=True)

            def submit(selector="main form"):
                page.locator(selector).locator("[type=submit]").click()

            def mail_link(kind):
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    for path in sorted(
                        runtime.mail_directory.glob("*.eml"),
                        key=lambda p: p.stat().st_mtime,
                        reverse=True,
                    ):
                        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
                        if message["To"] != email:
                            continue
                        body = message.get_body(preferencelist=("plain",)).get_content()
                        match = re.search(r"https?://[^\s]+/" + kind + r"/[^\s]+", body)
                        if match:
                            return match.group(0), message
                    page.wait_for_timeout(100)
                raise AssertionError("Erwartete lokale E-Mail fehlt")

            page.goto("/")
            shot("01-start")
            page.get_by_role("link", name="Konto erstellen", exact=True).first.click()
            page.locator("[name=username]").fill("Anleitung")
            page.locator("[name=email]").fill(email)
            for field in ("password", "password_confirm"):
                page.locator(f"[name={field}]").fill(password)
            shot("02-register")
            submit()
            page.wait_for_url("**/")
            shot("03-registration-sent")
            page.goto("/confirm")
            page.locator("[name=email]").fill(email)
            shot("04-resend-confirmation")
            submit()
            confirmation, message = mail_link("confirm")
            # Die echte HTML-Mail rendern, aber den privaten Bestätigungslink entfernen.
            mail_page = context.new_page()
            html = message.get_body(preferencelist=("html",)).get_content()
            html = re.sub(r'https?://[^\s"<>]+/confirm/[^\s"<>]+', "#confirmation-link", html)
            mail_page.set_content(html)
            mail_page.screenshot(path=str(output / "05-confirmation-email.png"), full_page=True)
            shots.append("05-confirmation-email")
            mail_page.close()
            page.goto(confirmation)
            page.locator("[name=identity]").fill(email)
            page.locator("[name=password]").fill(password)
            shot("06-login")
            submit()
            page.wait_for_url("**/")
            page.get_by_role("navigation").first.get_by_role(
                "link", name="Deine Geräte", exact=True
            ).click()
            shot("07-devices-empty")
            page.locator('a[href="/devices/new"]').click()
            for name, value in [
                ("name", "Werkstattradio"),
                ("manufacturer", "Beispielwerk"),
                ("model", "R10"),
            ]:
                page.locator(f"[name={name}]").fill(value)
            shot("08-device-new")
            submit("[data-device-form]")
            expect(page.locator("[data-saved-link]")).to_be_visible()
            shot("09-device-saved")
            page.locator("[data-saved-link]").click()
            device_url = page.url
            page.locator('a[href*="/edit"]').click()
            page.locator("[name=model]").fill("R10 Stereo")
            shot("10-device-edit")
            submit("[data-device-form]")
            expect(page.locator("[data-saved-link]")).to_be_visible()
            page.locator("[data-saved-link]").click()
            expect(page.locator(".device-details")).to_contain_text("R10 Stereo")

            def gallery(prefix):
                for index, color in enumerate(("#243b35", "#b84020", "#596660")):
                    picture = Image.new("RGB", (720, 480), color)
                    draw = ImageDraw.Draw(picture)
                    draw.rounded_rectangle(
                        (100, 100, 620, 380), radius=25, outline="white", width=8
                    )
                    draw.ellipse((150, 150, 330, 330), outline="white", width=8)
                    draw.line((390, 180, 560, 180), fill="white", width=8)
                    data = BytesIO()
                    picture.save(data, format="PNG")
                    page.locator("#image-file").set_input_files(
                        {
                            "name": f"Demobild-{index + 1}.png",
                            "mimeType": "image/png",
                            "buffer": data.getvalue(),
                        }
                    )
                    submit("[data-image-form]")
                    expect(page.locator(".image-tile")).to_have_count(index + 1)
                for img in page.locator(".image-tile img").all():
                    img.scroll_into_view_if_needed()
                    page.wait_for_function(
                        "img => img.complete && img.naturalWidth > 0", arg=img.element_handle()
                    )
                shot(prefix + "-gallery", "[data-image-gallery]")
                link = page.locator(".image-tile a").first.get_attribute("href")
                assert page.request.get(link).status == 200
                page.locator(".image-delete summary").first.click()
                shot(prefix + "-delete", "[data-image-gallery]")
                page.locator("[data-image-delete] button").first.click()
                expect(page.locator(".image-tile")).to_have_count(2)
                assert page.request.get(link).status == 404

            gallery("11-device")
            page.locator('a[href$="/repairs/new"]').click()
            page.locator("#new-description").fill(
                "Radio schaltet ein, aber aus dem Lautsprecher kommt kein Ton."
            )
            shot("12-repair-new")
            submit("[data-repair-form]")
            expect(page.locator("[data-total-cost]")).to_have_text("CHF 0.00")
            repair_url = page.url
            repair_id = repair_url.split("/repairs/")[1].split("?")[0]
            page.locator("#fault-description").fill(
                "Radio schaltet ein, aber der linke Lautsprecher bleibt stumm."
            )
            submit('form[action*="/description?"]')
            expect(page.locator("#fault-description")).to_have_attribute(
                "data-original", "Radio schaltet ein, aber der linke Lautsprecher bleibt stumm."
            )
            for description in [
                "Kabel und Steckverbindungen prüfen",
                "Lautsprecher ersetzen und Funktion prüfen",
            ]:
                page.locator("#new-step-description").fill(description)
                submit('form[action*="/steps?"]')
                expect(page.locator("#new-step-description")).to_have_value("")
            step = page.locator("[data-step-id]").first
            step.locator("textarea").fill("Steckverbindungen geprüft; Kabel sind intakt")
            step.locator("[type=checkbox]").check()
            step.locator("[type=submit]").click()
            expect(page.locator("[data-step-id]").first).to_have_class(re.compile("is-completed"))
            shot("13-steps", '[aria-labelledby="steps-heading"]')
            page.locator("#repair-status").select_option("in_progress")
            submit('form[action*="/status?"]')
            expect(page.locator(".repair-heading .repair-status")).to_have_text("In Bearbeitung")
            shot("14-description-status", ".repair-grid")
            page.locator("#work-hours").fill("2")
            page.locator("#work-rate").fill("80")
            submit('form[action*="/work?"]')
            expect(page.locator("[data-total-cost]")).to_have_text("CHF 160.00")
            for field, value in [
                ("name", "Ersatzlautsprecher"),
                ("price", "15"),
                ("quantity", "3"),
            ]:
                page.locator("#new-part-" + field).fill(value)
            submit('form[action*="/parts?"]')
            expect(page.locator("[data-total-cost]")).to_have_text("CHF 205.00")
            shot("15-costs", ".repair-grid.mt-4")
            shot("15-parts", '[aria-labelledby="parts-heading"]')
            part = page.locator("[data-part-id]").first
            part.locator("[name=name]").fill("Breitbandlautsprecher")
            part.locator("[type=submit]").click()
            expect(page.locator("[data-part-id]").first.locator("[name=name]")).to_have_attribute(
                "data-original", "Breitbandlautsprecher"
            )
            shot("16-part-edit", "[data-part-id]")
            # Die Galerie liegt ausserhalb des AJAX-Arbeitsbereichs und erscheint
            # nach Neuanlage erst beim vollständigen Öffnen der Detailseite.
            page.goto(repair_url)
            gallery("17-repair")
            for status, label in [
                ("completed", "Abgeschlossen"),
                ("in_progress", "In Bearbeitung"),
            ]:
                page.locator("#repair-status").select_option(status)
                submit('form[action*="/status?"]')
                expect(page.locator(".repair-heading .repair-status")).to_have_text(label)
            with page.expect_download() as pending:
                page.locator('a[href$="/report.pdf"]').click()
            pending.value.save_as(output.parent / "example-repair.pdf")
            pdf = PdfReader(output.parent / "example-repair.pdf")
            assert "205.00" in "\n".join(p.extract_text() for p in pdf.pages)
            shot("18-pdf-download", ".repair-workspace > p:has(a[href$='/report.pdf'])")
            page.goto("/devices/new")
            page.locator("[name=manufacturer]").fill("spiel")
            expect(page.locator("[data-suggestions] [role=option]").first).to_be_visible()
            shot("19-autocomplete")
            page.locator("[data-suggestions] [role=option]").first.click()
            expect(page.locator("[name=manufacturer]")).to_have_value("Beispielwerk")
            page.goto("/devices")
            page.locator("#device-search").fill("STEREO werk")
            expect(page.locator("[data-device-list]")).to_have_attribute("data-total", "1")
            shot("20-device-search")
            page.goto("/repairs")
            page.locator("#repair-search").fill("lautsprecher")
            page.locator("#repair-filter-status").select_option("in_progress")
            expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "1")
            shot("21-repair-search-status")
            page.locator("#repair-search").fill("kein passender Treffer")
            expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "0")
            shot("22-search-empty")
            page.locator("[data-filter-clear]").click()
            expect(page.locator("[data-repair-list]")).to_have_attribute("data-total", "1")
            page.goto("/account/api-key")
            shot("23-api-key-create")
            submit('form[action="/account/api-key"]')
            key = page.locator("#api-key-value").input_value()
            shot("24-api-key-generated")
            headers = {"Authorization": "Bearer " + key}
            assert page.request.get("/api/repairs", headers=headers).json()["total"] == 1
            assert (
                page.request.get("/api/repairs/" + repair_id, headers=headers).json()["costs"][
                    "total"
                ]
                == "205.00"
            )
            submit('form[action="/account/api-key"]')
            replacement = page.locator("#api-key-value").input_value()
            assert page.request.get("/api/repairs", headers=headers).status == 401
            assert (
                page.request.get(
                    "/api/repairs", headers={"Authorization": "Bearer " + replacement}
                ).status
                == 200
            )
            page.goto("/account/api-key")
            expect(page.locator("#api-key-value")).to_have_count(0)
            shot("25-api-key-manage")
            submit('form[action$="/revoke"]')
            assert (
                page.request.get(
                    "/api/repairs", headers={"Authorization": "Bearer " + replacement}
                ).status
                == 401
            )
            docker(
                "exec",
                runtime.app,
                "python",
                "-c",
                """
from sqlalchemy import select
from app import create_app
from app.extensions import db
from app.data.users.model import User
from app.data.devices.model import Device
from app.data.repairs.model import Repair
with create_app().app_context():
    user = db.session.scalar(select(User).where(User.username == 'Anleitung'))
    for i in range(100):
        device = Device(owner_id=user.id, name=f'Demogerät {i:03}',
                        manufacturer='Beispielwerk', model=f'Demo {i:03}')
        db.session.add(device)
        db.session.flush()
        db.session.add(Repair(device_id=device.id,
                      description=f'Demofall {i:03}: Funktionsprüfung', status='open'))
    db.session.commit()
""",
                capture=True,
            )
            for domain in ("devices", "repairs"):
                page.goto("/" + domain)
                rows = page.locator(
                    "[data-" + ("device" if domain == "devices" else "repair") + "-rows] > li"
                )
                expect(rows).to_have_count(60)
                viewport = page.locator("[data-list-viewport]")
                viewport.evaluate("element => element.scrollTop = 112 * 50 + 23")
                page.wait_for_timeout(700)
                assert rows.count() <= 60
                position = viewport.evaluate("element => element.scrollTop")
                shot("30-" + domain + "-scroll")
                # Playwrights Sichtbarkeit allein schliesst ausserhalb des Scrollfensters
                # liegende Zeilen nicht aus. Einen tatsächlich sichtbaren Link anklicken.
                bounds = viewport.bounding_box()
                for link in rows.locator('[data-action="view"]').all():
                    box = link.bounding_box()
                    if box and bounds["y"] + 10 < box["y"] < bounds["y"] + bounds["height"] - 40:
                        link.click()
                        break
                else:
                    raise AssertionError("Kein Link im sichtbaren Listenfenster")
                if domain == "devices":
                    page.locator("article.device-editor > a").first.click()
                else:
                    page.locator(".repair-breadcrumb a").first.click()
                expect(page.locator("[data-list-viewport]")).to_be_visible()
                page.wait_for_timeout(500)
                assert (
                    abs(
                        page.locator("[data-list-viewport]").evaluate(
                            "element => element.scrollTop"
                        )
                        - position
                    )
                    < 120
                )
            page.get_by_role("button", name="Abmelden").click()
            page.wait_for_url("**/")
            page.goto(device_url)
            page.wait_for_url("**/login")
            page.get_by_role("link", name="Passwort vergessen?").click()
            page.locator("[name=email]").fill(email)
            shot("26-password-request")
            submit()
            reset, _ = mail_link("reset")
            page.goto(reset)
            password = secrets.token_urlsafe(24)
            for field in ("password", "password_confirm"):
                page.locator(f"[name={field}]").fill(password)
            shot("27-password-reset")
            submit()
            page.wait_for_url("**/login")
            page.locator("[name=identity]").fill("Anleitung")
            page.locator("[name=password]").fill(password)
            submit()
            page.wait_for_url("**/")
            page.goto(repair_url)
            expect(page.locator("[data-total-cost]")).to_have_text("CHF 205.00")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            shot("28-mobile")
            page.set_viewport_size({"width": 1360, "height": 1000})
            page.goto("/page-does-not-exist")
            shot("29-not-found")
            assert not errors, errors
            browser.close()
    (output.parent / "capture.json").write_text(
        json.dumps(
            {
                "source_commit": commit,
                "locale": "de-CH",
                "isolation": "temporary production images, PostgreSQL, Garage and SMTP sink",
                "screenshots": shots,
                "passed": True,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, default=Path("docs/user-guide/images"))
    args = parser.parse_args()
    run(args.artifacts, args.commit, args.output)
