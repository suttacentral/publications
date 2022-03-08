from __future__ import annotations

import ast
import os
from pathlib import Path

import requests

from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, VolumeData

PAYLOADS_PATH = Path(__file__).parent / "example_payloads"
API_URL = os.getenv("API_URL")
API_ENDPOINTS = ast.literal_eval(os.getenv("API_ENDPOINTS", ""))


def get_mainmatter_data(edition_id: str, uids: list[str]) -> MainMatter:
    all_matters = []

    for uid in uids:
        response = requests.get(API_URL + API_ENDPOINTS["edition_mainmatter"].format(edition_id=edition_id, uid=uid))
        response.raise_for_status()
        payload = response.content

        all_matters.append(MainMatter.parse_raw(payload))

    result = all_matters[0]

    if the_rest := all_matters[1:]:
        # Move all to the first result
        result.__root__.extend(*the_rest)

    return result


def get_extras_data(edition_id: str) -> dict:
    response = requests.get(API_URL + API_ENDPOINTS["edition_files"].format(edition_id=edition_id))
    response.raise_for_status()
    response.content

    return dict(response.json())  # cast(dict, json.load(payload.decode('utf-8')))


def get_edition_data(edition_config: EditionConfig) -> EditionData:
    edition_data = EditionData()
    for volume_details in edition_config.edition.volumes:

        mainmatter = get_mainmatter_data(
            edition_id=edition_config.edition.edition_id,
            uids=volume_details.mainmatter,
        )
        extras = get_extras_data(edition_id=edition_config.edition.edition_id)
        edition_data.append(VolumeData(mainmatter=mainmatter, extras=extras))
    return edition_data
