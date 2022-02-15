import json
from copy import deepcopy
from pathlib import Path
from typing import Callable

import pytest

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.shared.config import Config, setup_inject

from fixtures.publisher import TestPublisher


@pytest.fixture(autouse=True)
def injector(get_file_path) -> Callable:
    """Configure application for the tests."""

    def _injector(
        publication_number: str = "test_publication",
        bindings: dict = None,
    ) -> None:
        bindings = bindings or {}
        actual_bindings = {
            ActivePublishers: ActivePublishers([TestPublisher()]),
            Config: Config(publication_number=publication_number, input_path=get_file_path("dn.tsv")),
        }
        actual_bindings.update(bindings)
        setup_inject(publication_number=publication_number, bindings=actual_bindings)

    return _injector


@pytest.fixture(scope="session")
def get_file_path():
    fixture_dir_path = Path(__file__).parent / "fixtures" / "data"

    def _get_file_path(f_name: str) -> Path:
        pth = fixture_dir_path / f_name
        return pth

    return _get_file_path


@pytest.fixture(scope="session")
def get_payload(get_file_path):
    payload_cache: dict[str, dict] = {}

    def _get_payload(file_name):
        if payload := payload_cache.get(file_name):
            return deepcopy(payload)

        if str(file_name).startswith("/"):
            # We got absolute path
            file_path = file_name
        else:
            # Relative path - construct the absolute path
            file_path = get_file_path(file_name)
        with open(file_path) as f:
            payload = json.load(f)
            payload_cache[file_name] = payload
        return deepcopy(payload)

    return _get_payload


@pytest.fixture(scope="session")
def get_data(get_file_path):
    payload_cache: dict[str, str] = {}

    def _get_data(file_name, mode="r"):
        if data := payload_cache.get(file_name):
            return deepcopy(data)

        if str(file_name).startswith("/"):
            # We got absolute path
            file_path = file_name
        else:
            # Relative path - construct the absolute path
            file_path = get_file_path(file_name)
        with open(file_path, mode=mode) as f:
            data = f.read()
            payload_cache[file_name] = data
        return deepcopy(data)

    return _get_data
