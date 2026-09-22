"""Echter PDF-Download aus der Detailseite, auch ohne JavaScript."""

from io import BytesIO

import pytest
from pypdf import PdfReader

from tests.e2e.test_devices import device_account as device_account
from tests.e2e.test_devices import login


@pytest.mark.parametrize("device_account", [1], indirect=True)
@pytest.mark.parametrize("page", [{"javascript": True, "locale": "de-CH"}, False], indirect=True)
def test_report_download(page, device_account):
    login(page, device_account)
    page.goto("/devices")
    page.locator('[data-action="view"]').first.click()
    page.locator('a[href$="/repairs/new"]').click()
    page.locator("#new-description").fill("Report download fault")
    page.locator("[data-repair-form] [type=submit]").click()
    link = page.locator('a[href$="/report.pdf"]')
    with page.expect_download() as pending:
        link.click()
    download = pending.value
    assert download.suggested_filename.startswith("repair-")
    assert download.suggested_filename.endswith(".pdf")
    with open(download.path(), "rb") as stream:
        reader = PdfReader(BytesIO(stream.read()))
    assert "Report download fault" in "\n".join(p.extract_text() for p in reader.pages)
