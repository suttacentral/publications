from pathlib import Path
from typing import Any

import pytest
import json
from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import MainMatterInfo, VolumeData, MainMatter, EditionData

RESOURCES_PATH = Path(__file__).parent.parent / "resources"


@pytest.fixture
def list_of_all_refs() -> list[str]:
    return [
        "ms",
        "pts-cs",
        "pts-vp-pli",
        "pts-vp-pli1ed",
        "pts-vp-pli2ed",
        "pts-vp-en",
        "vnp",
        "bj",
        "csp1ed",
        "csp2ed",
        "csp3ed",
        "dr",
        "mc",
        "mr",
        "si",
        "km",
        "lv",
        "ndp",
        "cck",
        "sya1ed",
        "sya2ed",
        "sya-all",
        "vri",
        "maku",
    ]


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
def base_parser(example_edition_config: EditionConfig, example_edition_data: EditionData) -> EditionParser:
    return EditionParser(config=example_edition_config, data=example_edition_data)


def test_should_parse_json_to_html(base_parser: EditionParser) -> None:
    generated_html = base_parser.collect_all()
    assert generated_html is not None
