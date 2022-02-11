from dataclasses import FrozenInstanceError

import pytest

from sutta_publisher.shared.value_objects.results import IngestResult


def test_should_prevent_content_modification():
    result = IngestResult(content="bazinga")
    with pytest.raises(FrozenInstanceError):
        # noinspection PyDataclass
        result.content = "dsa"
