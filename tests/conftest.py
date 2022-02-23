from io import BytesIO

import pytest


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
