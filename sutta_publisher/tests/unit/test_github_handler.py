import pytest

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
    result = github_handler.__match_file(filename, content)
    assert result == expected
