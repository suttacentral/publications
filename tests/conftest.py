from io import BytesIO
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
def file_like_edition() -> BytesIO:
    return BytesIO(b"Some very wise text to print")


@pytest.fixture
def edition_path_in_repo() -> str:
    return "path/in/repo/file.html"


@pytest.fixture
def bot_api_key() -> str:
    return "some_bot_api_key"


@pytest.fixture
def repo_url() -> str:
    return "https://github.com/someowner/somerepo/contents/"
