from base64 import b64encode
from io import BytesIO, StringIO

import pytest
from _pytest.monkeypatch import MonkeyPatch

from sutta_publisher.shared import github_handler


def test_generate_request_headers(bot_api_key: str) -> None:
    header = github_handler.__get_request_headers(bot_api_key)

    assert header["Authorization"] == f"token {bot_api_key}"


def test_generate_request_body(
    monkeypatch: MonkeyPatch, file_like_edition: BytesIO, edition_path_in_repo: str, repo_url: str
) -> None:
    monkeypatch.setattr(github_handler, "__get_file_sha", lambda *args: "someshanumber")

    body = github_handler.__get_request_body(file_like_edition, edition_path_in_repo, repo_url)

    file_like_edition.seek(0)

    assert body["message"] == f"Uploading {edition_path_in_repo}"
    assert body["content"] == b64encode(file_like_edition.read()).decode("ascii")
    assert body["sha"] == "someshanumber"


def test_raise_attribute_error(monkeypatch: MonkeyPatch, edition_path_in_repo: str, repo_url: str) -> None:
    monkeypatch.setattr(github_handler, "__get_file_sha", lambda *args: "someshanumber")

    file_content = "file_content"

    with pytest.raises(AttributeError):
        github_handler.__get_request_body(file_content, edition_path_in_repo, repo_url)


def test_raise_type_error(monkeypatch: MonkeyPatch, edition_path_in_repo: str, repo_url: str) -> None:
    monkeypatch.setattr(github_handler, "__get_file_sha", lambda *args: "someshanumber")

    file_content = StringIO("file_content")

    with pytest.raises(TypeError):
        github_handler.__get_request_body(file_content, edition_path_in_repo, repo_url)
