from unittest.mock import Mock

import pytest

from app.domains.devices.errors import AuthenticationRequired
from app.domains.devices.suggest_device_values.dto import Query
from app.domains.devices.suggest_device_values.handler import SuggestDeviceValues


def test_suggestions_scope_and_limit_are_enforced():
    repository = Mock()
    repository.suggest.return_value = ("R100",)
    assert SuggestDeviceValues(repository).execute(Query(7, "model", " R1 ", " Maker ")) == (
        "R100",
    )
    repository.suggest.assert_called_once_with(7, "model", ("r1",), "Maker", 10)


@pytest.mark.parametrize("owner", [None, 0, -1, True, "7"])
def test_untrusted_identity_cannot_search(owner):
    repository = Mock()
    with pytest.raises(AuthenticationRequired):
        SuggestDeviceValues(repository).execute(Query(owner, "name", "radio"))
    repository.suggest.assert_not_called()


@pytest.mark.parametrize(
    "field,term,manufacturer",
    [
        ("password", "ab", ""),
        ("name", "x" * 121, ""),
        ("model", "ab", "x" * 121),
        ("name", "a\x00b", ""),
        ("name", None, ""),
        ("model", "ab", "x\ny"),
    ],
)
def test_invalid_queries_are_rejected(field, term, manufacturer):
    repository = Mock()
    with pytest.raises(ValueError):
        SuggestDeviceValues(repository).execute(Query(7, field, term, manufacturer))
    repository.suggest.assert_not_called()


@pytest.mark.parametrize("term", ["", " ", "a", " a "])
def test_short_queries_do_not_reach_storage(term):
    repository = Mock()
    assert SuggestDeviceValues(repository).execute(Query(7, "name", term)) == ()
    repository.suggest.assert_not_called()


def test_manufacturer_does_not_filter_personal_names():
    repository = Mock()
    SuggestDeviceValues(repository).execute(Query(7, "name", "radio", "Maker"))
    repository.suggest.assert_called_once_with(7, "name", ("radio",), "", 10)


def test_search_parts_are_normalized_and_deduplicated():
    repository = Mock()
    SuggestDeviceValues(repository).execute(Query(7, "name", " RADIO  Küche radio "))
    repository.suggest.assert_called_once_with(7, "name", ("radio", "küche"), "", 10)
