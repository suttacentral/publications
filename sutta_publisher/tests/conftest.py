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


@pytest.fixture
def editions() -> list[dict]:
    return [
        {"edition_id": "snp-en-sujato_scpub17-ed2-epub_2022-02-10", "publication_number": "scpub17"},
        {"edition_id": "pli-tv-vi-en-brahmali_scpub8-ed2-epub_2022-02-10", "publication_number": "scpub8"},
    ]


@pytest.fixture
def publications() -> set[tuple]:
    return {
        ("scpub17", "en", "sujato", ("snp",)),
        (
            "scpub8",
            "en",
            "brahmali",
            (
                "pli-tv-vi",
                "pli-tv-bu-vb",
                "pli-tv-bi-vb",
                "pli-tv-kd",
                "pli-tv-pvr",
                "pli-tv-bu-pm",
                "pli-tv-bi-pm",
            ),
        ),
    }


@pytest.fixture
def super_tree() -> list[dict]:
    return [
        {
            "sutta": [
                {"long": ["dn"]},
                {"middle": ["mn"]},
                {"linked": ["sn"]},
                {"numbered": ["an"]},
                {
                    "minor": [
                        {
                            "kn": [
                                "dhp",
                                "ud",
                                "iti",
                                "snp",
                                "thag",
                                "thig",
                            ]
                        },
                    ]
                },
            ]
        },
        {
            "vinaya": [
                {
                    "pli-tv-vi": [
                        "pli-tv-bu-vb",
                        "pli-tv-bi-vb",
                        "pli-tv-kd",
                        "pli-tv-pvr",
                        "pli-tv-bu-pm",
                        "pli-tv-bi-pm",
                    ]
                },
            ]
        },
    ]
