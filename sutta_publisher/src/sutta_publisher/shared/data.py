from __future__ import annotations

from copy import deepcopy

import requests

from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import (
    EditionData,
    MainMatter,
    MainMatterPreheading,
    MainMatterPreheadings,
    PreheadingInfo,
    VolumeData,
)

API_URL = "http://localhost:80/api/"  # TODO: Change url for real one
API_ENDPOINTS = {
    "edition_mainmatter": "publication/edition/{edition_id}/{uid}",
    "edition_files": "publication/edition/{edition_id}/files",
}


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


def get_mainmatter_preheadings(edition_id: str, uids: list[str]) -> MainMatterPreheadings:
    all_uids_preheadings = MainMatterPreheadings()

    for uid in uids:
        response = requests.get(API_URL + API_ENDPOINTS["edition_mainmatter"].format(edition_id=edition_id, uid=uid))
        response.raise_for_status()
        nodes = response.json()

        per_mainmatter_preheading = (
            MainMatterPreheading()
        )  # a collection of headings to put before <article> tag of each mainmatter

        for node in nodes[1:]:  # we want to skip the main uid
            if node["type"] == "branch":
                per_mainmatter_preheading.append(PreheadingInfo.parse_raw(node))
            elif node["type"] == "leaf" and per_mainmatter_preheading:
                # reached the end of preheadings for one mainmatter
                # copy the list for that mainmatter to a higher order container (with all mainmatters per uid)
                all_uids_preheadings.append(deepcopy(per_mainmatter_preheading))
                # and reset the list - start new collection for another mainmatter
                MainMatterPreheadings()

    return all_uids_preheadings


# def _calculate_nesting_depth(payload: dict) -> int:
#     nesting_depth = 0
#     next_key = next(iter(payload))
#     while True:
#         if type(payload[next_key]) is list:
#             nesting_depth += 1
#             payload = payload[next_key][0]
#             if type(payload[0]) is str:
#                 break
#             else:
#                 next_key = next(iter(payload))
#     return nesting_depth
#
#
# def _get_child_if_collection(obj: list | dict) -> list | dict | None:
#     if type(obj) is dict:
#         first_key = next(iter(obj))
#         return obj[first_key]  # type: ignore
#     else:
#         return obj[0]  # type: ignore


def get_extras_data(edition_id: str) -> dict:
    response = requests.get(API_URL + API_ENDPOINTS["edition_files"].format(edition_id=edition_id))
    response.raise_for_status()

    return dict(response.json())  # cast(dict, json.load(payload.decode('utf-8')))


def get_edition_data(edition_config: EditionConfig) -> EditionData:
    edition_data = EditionData()
    for volume_details in edition_config.edition.volumes:
        preheadings = get_mainmatter_preheadings(
            edition_id=edition_config.edition.edition_id,
            uids=volume_details.mainmatter,
        )
        mainmatter = get_mainmatter_data(
            edition_id=edition_config.edition.edition_id,
            uids=volume_details.mainmatter,
        )
        extras = get_extras_data(edition_id=edition_config.edition.edition_id)
        edition_data.append(VolumeData(preheadings=preheadings, mainmatter=mainmatter, extras=extras))
    return edition_data
