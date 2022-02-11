from typing import Callable

import pytest

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.shared.config import setup_inject

from fixtures.publisher import TestPublisher


@pytest.fixture
def injector() -> Callable:
    """Configure application for the tests."""

    def _injector(publication_number: str = "test_publication", bindings: dict = None) -> None:
        bindings = bindings or {}
        actual_bindings = {ActivePublishers: ActivePublishers([TestPublisher()])}
        actual_bindings.update(bindings)
        setup_inject(publication_number=publication_number, bindings=actual_bindings)

    return _injector


@pytest.fixture
def scpub1_data() -> dict:
    """Data of scpub1 publication."""

    data: dict = {
        "publication_number": "scpub1",
        "creator_name": "Bhikkhu Sujato",
        "translation_title": "Verses of the Senior Monks",
        "translation_subtitle": "An approachable translation of the Theragāthā",
        "root_title": "Theragāthā",
    }

    # TODO: remove below dummy editions when Config class is fully functional
    data["editions"] = {"key1": "val1", "key2": "val1", "key3": "val1", "key4": {"key1": "val1", "key2": "val"}}

    return data
