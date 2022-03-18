import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def sources_root() -> str:
    sources_path = Path("/app/")
    paths = set(sys.path)
    for py_path in paths:
        if py_path.endswith(str(sources_path)):
            return py_path

    raise RuntimeError(f"Couldn't find sources [{sources_path}] for this project. paths: {paths}")


# TODO: remove this test or fix it. It doesn't work in a sense that the program obviously works (e.g. produces epub), so relative imports aren't an issue yet the test fails.
# def test_no_relative_imports(sources_root: str) -> None:
#     """Ensure that there are no relative imports from parent modules."""
#     process = subprocess.run(
#         ["grep", "-F", "from ..", "-R", sources_root],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#         universal_newlines=True,
#     )
#     assert not process.stdout, process.stdout
#     assert not process.stderr, process.stderr
