from unittest import mock

import pytest
from requests.models import Response

from sutta_publisher.shared import github_handler


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
    responses = github_handler.worker(request, "test_key")
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
    responses = github_handler.worker(request, "test_key")
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
        github_handler.worker(request, "test_key")
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

    ret = github_handler.worker(request, "test_key", silent=True)
    assert mock_get.call_count == 3
    assert ret == []


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
