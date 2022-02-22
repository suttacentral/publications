import json

import pytest

from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.config import PAYLOADS_PATH


@pytest.fixture
def list_of_all_refs():
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
def payload() -> dict:
    return json.load(open(PAYLOADS_PATH / "mn-en-sujato_scpub3-ed6-html_2022-02-10-mn.json"))


@pytest.fixture
def base_parser() -> EditionParser:
    pass


# this is more of a sandbox than a test
def test_base_parser(payload, list_of_all_refs):
    volumes: list[dict] = [volume for volume in payload]
    output: list[str] = []
    for volume in volumes:
        volume_html: str = []
        volume_text: dict[str, str] = volume.get("mainmatter").get("main_text") if not None else {}
        volume_markup: dict[str, str] = volume.get("mainmatter").get("markup")
        volume_references: dict[str, str] = volume.get("mainmatter").get("reference")
        # for segment_id in volume_text.keys():
        #     _process_a_line(
        #         markup=volume_markup[segment_id],
        #         segment_id=segment_id,
        #         text=volume_text[segment_id],
        #         references=volume_references[segment_id],
        #         possible_refs=list_of_all_refs,
        #     )
