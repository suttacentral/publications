from base64 import b64encode
from pathlib import Path

import pytest
from _pytest.monkeypatch import MonkeyPatch

from sutta_publisher.shared import github_handler


def test_generate_request_headers(bot_api_key: str) -> None:
    header = github_handler.__get_request_headers(bot_api_key)

    assert header["Accept"] == "application/vnd.github+json"
    assert header["Authorization"] == f"token {bot_api_key}"


def test_generate_request_body(monkeypatch: MonkeyPatch, file_path: Path, repo_url: str) -> None:
    monkeypatch.setattr(github_handler, "__get_file_sha", lambda *args: "someshanumber")
    monkeypatch.setattr(Path, "read_bytes", lambda *args: b"Some file content")

    body = github_handler.__get_request_body(file_path, repo_url)

    assert body["message"] == f"Uploading {file_path.name}"
    assert body["content"] == b64encode(file_path.read_bytes()).decode("ascii")
    assert body["sha"] == "someshanumber"


def test_raise_type_error(monkeypatch: MonkeyPatch, file_path: Path, repo_url: str) -> None:
    monkeypatch.setattr(github_handler, "__get_file_sha", lambda *args: "someshanumber")
    monkeypatch.setattr(Path, "read_bytes", lambda *args: "file_content")

    with pytest.raises(TypeError):
        github_handler.__get_request_body(file_path, repo_url)


@pytest.mark.parametrize(
    "filename, content, expected",
    [
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12.zip",
            [{"name": "Sayings-of-the-Dhamma-sujato-2022-10-12.zip"}],
            {"name": "Sayings-of-the-Dhamma-sujato-2022-10-12.zip"},
        ),
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12.zip",
            [{"name": "Sayings-of-the-Dhamma-sujato-2022-9-1.zip"}],
            {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1.zip"},
        ),
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12-3.zip",
            [{"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-3.zip"}],
            {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-3.zip"},
        ),
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12-3.zip",
            [
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-1.zip"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-2.zip"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-3.zip"},
            ],
            {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-3.zip"},
        ),
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12.zip",
            [
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-1.zip"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-2.zip"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-9-1-3.zip"},
            ],
            {},
        ),
        ("Sayings-of-the-Dhamma-sujato-2022-10-12-1.zip", [{"name": "Sayings-of-the-Dhamma-sujato-2022-9-1.zip"}], {}),
    ],
)
def test_match_file(filename: str, content: list[dict], expected: dict) -> None:
    result = github_handler.__match_file(filename, content)
    assert result == expected
