"""Beide Fachdomänen schützen Upload, Liste und Abruf vor fremdem Zugriff."""

import importlib
from unittest.mock import Mock

import pytest


@pytest.fixture(params=["devices", "repairs"])
def domain(request):
    base = "app.domains." + request.param
    return lambda name: importlib.import_module(base + "." + name)


def test_upload_checks_ownership_before_decoding_or_storage(domain):
    repository, processor, storage = Mock(), Mock(), Mock()
    repository.owns.return_value = False
    handler = domain("upload_image.handler").UploadImage(
        repository, processor, storage, lambda: "a" * 32
    )
    with pytest.raises(domain("errors").ImageNotFound):
        handler.execute(domain("upload_image.dto").Command(1, 8, "image.png", b"image"))
    processor.prepare.assert_not_called()
    storage.put.assert_not_called()


@pytest.mark.parametrize(
    "filename,body",
    [
        ("../image.png", b"x"),
        ("C:\\image.jpg", b"x"),
        ("", b"x"),
        ("a\x00.jpg", b"x"),
        ("image.png", b""),
        ("image.png", b"x" * (10 * 1024 * 1024 + 1)),
    ],
)
def test_invalid_upload_never_reaches_processor(domain, filename, body):
    repository, processor, storage = Mock(), Mock(), Mock()
    repository.owns.return_value = True
    handler = domain("upload_image.handler").UploadImage(
        repository, processor, storage, lambda: "a" * 32
    )
    with pytest.raises(domain("errors").InvalidImage):
        handler.execute(domain("upload_image.dto").Command(1, 8, filename, body))
    processor.prepare.assert_not_called()


def test_prepared_blobs_are_stored_before_metadata(domain):
    repo, processor, storage = Mock(), Mock(), Mock()
    repo.owns.return_value = True
    processor.prepare.return_value = (b"original", b"thumbnail", 800, 600)
    handler = domain("upload_image.handler").UploadImage(repo, processor, storage, lambda: "a" * 32)
    result = handler.execute(domain("upload_image.dto").Command(1, 8, "repair.jpg", b"source"))
    assert result.id == "a" * 32
    storage.put.assert_any_call("images/" + "a" * 32 + ".webp", b"original", "image/webp")
    storage.put.assert_any_call("images/" + "a" * 32 + "-thumb.webp", b"thumbnail", "image/webp")
    repo.add.assert_called_once_with(1, 8, result)


def test_storage_failure_does_not_publish_metadata(domain):
    repo, processor, storage = Mock(), Mock(), Mock()
    repo.owns.return_value = True
    processor.prepare.return_value = (b"original", b"thumbnail", 800, 600)
    storage.put.side_effect = OSError()
    with pytest.raises(domain("errors").ImageUnavailable):
        domain("upload_image.handler").UploadImage(
            repo, processor, storage, lambda: "a" * 32
        ).execute(domain("upload_image.dto").Command(1, 8, "image.jpg", b"source"))
    repo.add.assert_not_called()


def test_foreign_image_never_reads_object_store(domain):
    repo, storage = Mock(), Mock()
    repo.get.return_value = None
    with pytest.raises(domain("errors").ImageNotFound):
        domain("get_image.handler").GetImage(repo, storage).execute(
            domain("get_image.dto").Command(1, 8, "a" * 32)
        )
    storage.read.assert_not_called()


@pytest.mark.parametrize("owner", [None, 0, -1, True, "1"])
def test_invalid_identity_never_queries_repository(domain, owner):
    repo = Mock()
    with pytest.raises(domain("errors").AuthenticationRequired):
        domain("list_images.handler").ListImages(repo).execute(
            domain("list_images.dto").Command(owner, 8)
        )
    repo.owns.assert_not_called()


@pytest.mark.parametrize("removed", [True, False])
def test_delete_requires_owned_image(domain, removed):
    repo = Mock()
    repo.delete.return_value = removed
    handler = domain("delete_image.handler").DeleteImage(repo)
    command = domain("delete_image.dto").Command(1, 8, "a" * 32)
    if removed:
        assert handler.execute(command) is None
    else:
        with pytest.raises(domain("errors").ImageNotFound):
            handler.execute(command)
    repo.delete.assert_called_once_with(1, 8, "a" * 32)


def test_delete_rejects_manipulated_identifier_before_repository(domain):
    repo = Mock()
    with pytest.raises(domain("errors").ImageNotFound):
        domain("delete_image.handler").DeleteImage(repo).execute(
            domain("delete_image.dto").Command(1, 8, "../image")
        )
    repo.delete.assert_not_called()


def test_delete_maps_repository_failure(domain):
    repo = Mock()
    repo.delete.side_effect = OSError("private database details")
    with pytest.raises(domain("errors").ImageUnavailable):
        domain("delete_image.handler").DeleteImage(repo).execute(
            domain("delete_image.dto").Command(1, 8, "a" * 32)
        )
