import sys
from pathlib import Path

import pytest

sys.path.insert(0, "/app")


@pytest.fixture
def file_path() -> Path:
    return Path("path/in/repo/file.html")


@pytest.fixture
def bot_api_key() -> str:
    return "some_bot_api_key"


@pytest.fixture
def repo_url() -> str:
    return "https://github.com/someowner/somerepo/contents/"
