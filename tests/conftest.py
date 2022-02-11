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
