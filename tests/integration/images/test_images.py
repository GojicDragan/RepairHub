"""HTTP, PostgreSQL und Garage prüfen dieselbe Eigentumskette bis zum Pixelabruf."""

import io
import re
import tarfile
import time

import pytest

from app.data.files.backup import backup
from tests.integration.devices.test_devices import csrf, save
from tests.integration.devices.test_devices import owner as owner
from tests.integration.repairs.test_repairs import create
from tests.integration.users.test_registration import PASSWORD, confirmation, register, submit
from tests.unit.data.files.test_image_processor import encoded


@pytest.fixture(params=["devices", "repairs"])
def target(request, owner):
    parent = save(owner).json["device"]["id"] if request.param == "devices" else create(owner)
    return f"/{request.param}/{parent}/images"


def upload(owner, target, content=None, filename="image.png", token=True):
    data = {"image": (io.BytesIO(encoded() if content is None else content), filename)}
    if token:
        data["csrf_token"] = csrf(owner)
    return owner.post(
        target,
        data=data,
        headers={"Accept": "application/json", "Referer": "https://localhost" + target},
    )


def test_upload_mosaic_and_private_original(owner, target, garage):
    result = upload(owner, target)
    assert result.status_code == 201
    html = result.json["html"]
    assert 'class="image-mosaic"' in html
    assert 'loading="lazy"' in html
    path = re.search(r'href="([^"]+/images/[a-f0-9]{32})"', html)[1]
    for url in (path, path + "?thumbnail=1"):
        response = owner.get(url)
        assert response.status_code == 200
        assert response.content_type == "image/webp"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "no-store" in response.headers["Cache-Control"]
        assert response.data[:4] == b"RIFF"
    assert "http://garage" not in html and "S3_" not in html
    original = owner.get(path).data
    garage["docker"]("restart", garage["container"])
    for _attempt in range(30):
        response = owner.get(path)
        if response.status_code == 200:
            break
        time.sleep(0.2)
    assert response.data == original


def test_foreign_parent_image_and_anonymous_access(owner, target, identity_app):
    result = upload(owner, target)
    path = re.search(r'href="([^"]+/images/[a-f0-9]{32})"', result.json["html"])[1]
    foreign = identity_app.test_client()
    register(foreign, username="ImageOther", email="images-other@example.org")
    foreign.get(confirmation(identity_app))
    submit(foreign, "/login", identity="ImageOther", password=PASSWORD)
    for client in (foreign,):
        assert client.get(target).status_code == 404
        assert client.get(path).status_code == 404
        assert upload(client, target).status_code == 404
    anonymous = identity_app.test_client()
    assert anonymous.get(path).status_code == 401
    assert owner.get(target + "/../secret").status_code == 404
    assert owner.get(target + "/" + "f" * 32).status_code == 404


@pytest.mark.parametrize(
    "content,filename",
    [
        (b"not an image", "valid.png"),
        (b"%PDF-1.7", "file.pdf"),
        (encoded(), "../escape.png"),
        (encoded()[:30], "truncated.png"),
        (b"x" * (10 * 1024 * 1024 + 1), "large.png"),
    ],
)
def test_invalid_images_rejected(owner, target, content, filename):
    assert upload(owner, target, content, filename).status_code == 422
    assert "No images yet." in owner.get(target).text


def test_csrf_and_no_js_upload(owner, target):
    assert upload(owner, target, token=False).status_code == 400
    response = owner.post(
        target,
        headers={"Referer": "https://localhost" + target},
        data={
            "csrf_token": csrf(owner),
            "image": (io.BytesIO(encoded()), "portrait.png"),
        },
    )
    assert response.status_code == 303
    assert "#images" in response.location
    assert 'class="image-mosaic"' in owner.get(response.location).text


def test_object_backup_has_manifest_and_private_images(owner, target, garage, tmp_path):
    assert upload(owner, target).status_code == 201
    path = tmp_path / "files.tar"
    backup(garage["storage"], path)
    with tarfile.open(path) as archive:
        assert "manifest.json" in archive.getnames()
        assert any(name.startswith("objects/images/") for name in archive.getnames())
        assert all(member.isfile() for member in archive.getmembers())
    with pytest.raises(FileExistsError):
        backup(garage["storage"], path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_gallery_is_bounded_and_new_upload_is_first(owner, target):
    for index in range(26):
        assert upload(owner, target, filename=f"Photo {index:02}.png").status_code == 201
    first = owner.get(target).text
    second = owner.get(target + "?image_offset=24").text
    assert first.count('class="image-tile ') == 24
    assert second.count('class="image-tile ') == 2
    assert first.index("Photo 25.png") < first.index("Photo 24.png")
    assert "26 images" in first
    assert "Photo 00.png" not in first and "Photo 00.png" in second
    assert owner.get(target + "?image_offset=-1").status_code == 400


@pytest.mark.parametrize("ajax", [True, False])
def test_delete_is_private_csrf_protected_and_removes_access(owner, target, identity_app, ajax):
    result = upload(owner, target)
    path = re.search(r'href="([^"]+/images/[a-f0-9]{32})"', result.json["html"])[1]
    delete_url = path + "/delete"
    headers = {"Referer": "https://localhost" + target}
    if ajax:
        headers["Accept"] = "application/json"
    assert owner.get(delete_url).status_code == 405
    assert owner.post(delete_url, headers=headers).status_code == 400
    foreign = identity_app.test_client()
    register(foreign, username="DeleteOther", email="delete-other@example.org")
    foreign.get(confirmation(identity_app))
    submit(foreign, "/login", identity="DeleteOther", password=PASSWORD)
    assert (
        foreign.post(delete_url, data={"csrf_token": csrf(foreign)}, headers=headers).status_code
        == 404
    )
    assert owner.get(path).status_code == 200
    response = owner.post(delete_url, data={"csrf_token": csrf(owner)}, headers=headers)
    assert response.status_code == (200 if ajax else 303)
    assert owner.get(path).status_code == 404
    assert owner.get(path + "?thumbnail=1").status_code == 404
    assert (
        owner.post(delete_url, data={"csrf_token": csrf(owner)}, headers=headers).status_code == 404
    )
    if ajax:
        assert 'class="image-tile ' not in response.json["html"]
        assert response.json["message"] == "Image deleted."
    else:
        assert response.headers["Location"].endswith("#images")
