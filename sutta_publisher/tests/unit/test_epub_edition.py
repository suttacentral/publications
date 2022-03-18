import json
from pathlib import Path
from typing import Any

import pytest

from sutta_publisher.edition_parsers.epub import EpubEdition
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, MainMatterInfo, VolumeData

RESOURCES_PATH = Path("/app/sutta_publisher/shared/example_payloads/")


@pytest.fixture
def example_data_payload() -> list[dict[str, Any]]:
    return json.load(open(RESOURCES_PATH / "mn-en-sujato_scpub3-ed6-html_2022-02-10-mn.json"))  # type: ignore


@pytest.fixture
def example_config_payload() -> dict[str, Any]:
    return json.load(open(RESOURCES_PATH / "mn-en-sujato_scpub3-ed6-html_2022-02-10.json"))  # type: ignore


@pytest.fixture
def example_edition_config(example_config_payload: dict[str, Any]) -> EditionConfig:
    return EditionConfig(**example_config_payload)


@pytest.fixture
def single_volume(example_data_payload: list[dict[str, Any]]) -> VolumeData:
    mainmatter_list: list[MainMatterInfo] = []
    for main_matter_info in example_data_payload:
        mainmatter_list.append(MainMatterInfo(**main_matter_info))
    actual_mainmatter = MainMatter(__root__=mainmatter_list)

    return VolumeData(mainmatter=actual_mainmatter, extras={})


@pytest.fixture
def example_edition_data(single_volume: VolumeData) -> EditionData:
    return EditionData([single_volume])


@pytest.fixture
def base_parser(example_edition_config: EditionConfig, example_edition_data: EditionData) -> EpubEdition:
    return EpubEdition(config=example_edition_config, data=example_edition_data)


def test_should_parse_json_to_html(epub_parser: EpubEdition) -> None:
    assert (result := epub_parser.collect_all()) is not None
