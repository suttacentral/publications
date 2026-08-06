import json
from unittest import mock

import pytest
from requests.models import Response

from sutta_publisher.shared import github_handler


def make_response(payload: dict | list, status_code: int = 200) -> Response:
    response = Response()
    response.status_code = status_code
    response.json = lambda: payload
    return response


@mock.patch("sutta_publisher.shared.github_handler.requests.post")
@mock.patch("sutta_publisher.shared.github_handler.requests.get")
def test_upload_replaces_existing_directory_contents(mock_get: mock.Mock, mock_post: mock.Mock, tmp_path) -> None:
    new_file = tmp_path / "Sayings-of-the-Dhamma-sujato-2026-08-05.zip"
    new_file.write_bytes(b"new publication")

    mock_get.side_effect = [
        make_response(
            {
                "commit": {
                    "sha": "last-commit-sha",
                    "commit": {"tree": {"sha": "base-tree-sha"}},
                }
            }
        ),
        make_response(
            [
                {
                    "name": "Sayings-of-the-Dhamma-sujato-2026-07-01.zip",
                    "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-07-01.zip",
                    "type": "file",
                    "sha": "old-blob-sha",
                },
                {
                    "name": "Sayings-of-the-Dhamma-sujato-2026-07-01-3.zip",
                    "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-07-01-3.zip",
                    "type": "file",
                    "sha": "old-third-volume-blob-sha",
                },
                {
                    "name": "Sayings-of-the-Dhamma-sujato-2026-08-05.zip",
                    "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-08-05.zip",
                    "type": "file",
                    "sha": "current-blob-sha",
                },
                {
                    "name": "assets",
                    "path": "en/sujato/dhp/paperback/assets",
                    "type": "dir",
                    "sha": "assets-tree-sha",
                },
            ]
        ),
    ]
    mock_post.side_effect = [
        make_response({"sha": "new-blob-sha"}),
        make_response({"sha": "new-tree-sha"}),
        make_response({"sha": "new-commit-sha"}),
        make_response({}),
    ]

    github_handler.upload_files_to_repo(
        file_paths=[new_file],
        repo_url="https://api.github.com/repos/example/editions",
        repo_path="en/sujato/dhp/paperback",
        api_key="test-key",
        replace_directory=True,
    )

    tree_request = next(
        call
        for call in mock_post.call_args_list
        if call.kwargs["url"] == "https://api.github.com/repos/example/editions/git/trees"
    )
    assert json.loads(tree_request.kwargs["data"])["tree"] == [
        {
            "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-07-01.zip",
            "mode": "100644",
            "type": "blob",
            "sha": None,
        },
        {
            "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-07-01-3.zip",
            "mode": "100644",
            "type": "blob",
            "sha": None,
        },
        {
            "path": "en/sujato/dhp/paperback/Sayings-of-the-Dhamma-sujato-2026-08-05.zip",
            "mode": "100644",
            "type": "blob",
            "sha": "new-blob-sha",
        },
    ]


@mock.patch("sutta_publisher.shared.github_handler.requests.post")
@mock.patch("sutta_publisher.shared.github_handler.requests.get")
def test_upload_preserves_directory_contents_by_default(mock_get: mock.Mock, mock_post: mock.Mock, tmp_path) -> None:
    new_file = tmp_path / "last_run_date"
    new_file.write_text("2026-08-05T10:00:00Z")

    mock_get.return_value = make_response(
        {
            "commit": {
                "sha": "last-commit-sha",
                "commit": {"tree": {"sha": "base-tree-sha"}},
            }
        }
    )
    mock_post.side_effect = [
        make_response({"sha": "new-blob-sha"}),
        make_response({"sha": "new-tree-sha"}),
        make_response({"sha": "new-commit-sha"}),
        make_response({}),
    ]

    github_handler.upload_files_to_repo(
        file_paths=[new_file],
        repo_url="https://api.github.com/repos/example/editions",
        repo_path="",
        api_key="test-key",
    )

    assert [call.kwargs["url"] for call in mock_get.call_args_list] == [
        "https://api.github.com/repos/example/editions/branches/main"
    ]
    tree_request = next(
        call
        for call in mock_post.call_args_list
        if call.kwargs["url"] == "https://api.github.com/repos/example/editions/git/trees"
    )
    assert json.loads(tree_request.kwargs["data"])["tree"] == [
        {
            "path": "last_run_date",
            "mode": "100644",
            "type": "blob",
            "sha": "new-blob-sha",
        }
    ]


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
        (
            "Sayings-of-the-Dhamma-sujato-2022-10-12.zip",
            [
                {"name": "Sayings-of-the-Dhamma-sujato-2022-10-12.pdf"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-10-12-cover.pdf"},
                {"name": "Sayings-of-the-Dhamma-sujato-2022-10-12.zip"},
            ],
            {"name": "Sayings-of-the-Dhamma-sujato-2022-10-12.zip"},
        ),
    ],
)
def test_match_file(filename: str, content: list[dict], expected: dict) -> None:
    result = github_handler.match_file(filename, content)
    assert result == expected


@mock.patch("sutta_publisher.shared.github_handler.requests.get")
def test_worker_success(mock_get) -> None:
    mock_response = Response()
    mock_response.status_code = 200
    mock_response.json = lambda: {}
    mock_get.return_value = mock_response

    request = {
        "method": "get",
        "url": "https://example.com/repo_url",
        "type": "test",
    }
    responses = github_handler.worker([request], "test_key")
    assert len(responses) == 1
    mock_get.assert_called_once_with(
        url="https://example.com/repo_url",
        headers={"Accept": "application/vnd.github+json", "Authorization": "Token test_key"},
        data=None,
    )


@mock.patch("sutta_publisher.shared.github_handler.requests.get")
@mock.patch("sutta_publisher.shared.github_handler.sleep")
def test_worker_success_with_one_fail(mock_sleep, mock_get: mock.Mock) -> None:
    mock_responses = []
    for i in range(3):
        mock_response = Response()
        mock_response.status_code = 404 if i < 2 else 200
        mock_response.json = lambda: {}
        mock_responses.append(mock_response)

    mock_get.side_effect = mock_responses

    request = {
        "method": "get",
        "url": "https://example.com/repo_url",
        "type": "test",
    }
    responses = github_handler.worker([request], "test_key")
    assert len(responses) == 1
    assert mock_get.call_count == 3
    mock_get.assert_called_with(
        url="https://example.com/repo_url",
        headers={"Accept": "application/vnd.github+json", "Authorization": "Token test_key"},
        data=None,
    )


@mock.patch("sutta_publisher.shared.github_handler.requests.get")
@mock.patch("sutta_publisher.shared.github_handler.sleep")
def test_worker_raises(mock_sleep, mock_get) -> None:
    mock_response = Response()
    mock_response.status_code = 404
    mock_response.json = lambda: {}
    mock_get.return_value = mock_response

    request = {
        "method": "get",
        "url": "https://example.com/repo_url",
        "type": "test",
    }

    with pytest.raises(SystemExit):
        github_handler.worker([request], "test_key")
        assert mock_get.call_count == 3


@mock.patch("sutta_publisher.shared.github_handler.requests.get")
@mock.patch("sutta_publisher.shared.github_handler.sleep")
def test_worker_silent(mock_sleep, mock_get) -> None:
    mock_response = Response()
    mock_response.status_code = 404
    mock_response.json = lambda: {}
    mock_get.return_value = mock_response

    request = {
        "method": "get",
        "url": "https://example.com/repo_url",
        "type": "test",
    }

    response = github_handler.worker([request], "test_key", silent=True)
    assert mock_get.call_count == 3
    assert response == []


@mock.patch("sutta_publisher.shared.github_handler.requests.get")
@mock.patch("sutta_publisher.shared.github_handler.sleep")
def test_worker_return_is_sorted(mock_sleep, mock_get: mock.Mock) -> None:
    """The order of worker()'s return should be the same as input"""
    test_data = (
        (404, 1),
        (200, 2),
        (404, 3),
        (404, 1),
        (200, 3),
        (200, 1),
    )

    mock_responses = []
    for _status_code, _task_index in test_data:
        mock_response = Response()
        mock_response.status_code = _status_code
        mock_response.json = lambda: {}
        mock_response.task_index = _task_index
        mock_responses.append(mock_response)

    mock_get.side_effect = mock_responses

    _requests = [
        {
            "method": "get",
            "url": "https://example.com/repo_url",
            "type": "test",
        }
        for _ in range(3)
    ]
    responses = github_handler.worker(_requests, "test_key")
    assert len(responses) == 3
    assert mock_get.call_count == len(test_data)
    assert responses == sorted(responses, key=lambda x: x.task_index)
