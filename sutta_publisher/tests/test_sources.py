import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def sources_root() -> str:
    sources_path = Path("/src")
    paths = set(sys.path)
    for py_path in paths:
        if py_path.endswith(str(sources_path)):
            return py_path

    raise RuntimeError(f"Couldn't find sources [{sources_path}] for this project. paths: {paths}")


def test_no_relative_imports(sources_root):
    """Ensure that there are no relative imports from parent modules."""
    process = subprocess.run(
        ["grep", "-F", "from ..", "-R", sources_root],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    assert not process.stdout, process.stdout
    assert not process.stderr, process.stderr
