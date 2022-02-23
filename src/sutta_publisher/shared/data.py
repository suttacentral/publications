from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, VolumeData

PAYLOADS_PATH = Path(__file__).parent / "example_payloads"


def get_mainmatter_data(edition_id: str, uids: list[str]) -> MainMatter:
    # TODO: [#20] Get data from real api
    all_matters = []
    for uid in uids:
        f_path = PAYLOADS_PATH / f"{edition_id}-{uid}.json"
        with open(f_path) as f:
            payload = f.read()
        all_matters.append(MainMatter.parse_raw(payload))
    result = all_matters[0]
    if the_rest := all_matters[1:]:
        # Move all to the first result
        result.__root__.extend(*the_rest)
    return result


def get_extras_data(edition_id: str) -> dict:
    # TODO: [#20] Get data from real api
    f_path = PAYLOADS_PATH / f"{edition_id}-files.json"
    with open(f_path) as f:
        return cast(dict, json.load(f))


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
