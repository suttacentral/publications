from __future__ import annotations

import ast
import os
from copy import deepcopy

import requests

from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import (
    EditionData,
    Heading,
    HeadingsGroup,
    MainMatter,
    MainMatterHeadings,
    MainMatterPart,
    MainMatterPreheadings,
    Preheading,
    PreheadingsGroup,
    VolumeData,
    VolumeHeadings,
    VolumePreheadings,
)

API_URL = os.getenv("API_URL")
API_ENDPOINTS = ast.literal_eval(os.getenv("API_ENDPOINTS", ""))
TREE_URL = os.getenv("TREE_URL", "")


def get_mainmatter_data(edition_id: str, uids: list[str]) -> MainMatter:
    _all_parts: list[MainMatterPart] = []

    for uid in uids:
        response = requests.get(API_URL + API_ENDPOINTS["edition_mainmatter"].format(edition_id=edition_id, uid=uid))
        response.raise_for_status()
        payload = response.content

        _all_parts.append(MainMatterPart.parse_raw(payload))

    # result = all_matters[0]
    #
    # if the_rest := all_matters[1:]:
    #     # Move all to the first result
    #     result.__root__.extend(*the_rest)

    return MainMatter.parse_obj(_all_parts)


def get_depths(tree: list[dict] | list[str], depths: dict[str, int], initial_depth: int = 1) -> None:
    """Get all headings depth recursively"""
    for item in tree:
        if isinstance(item, dict):
            depths[list(item.keys())[0]] = initial_depth
            _tree = list(item.values())[0]
            get_depths(_tree, depths, initial_depth=initial_depth + 1)
        elif isinstance(item, str):
            depths[item] = initial_depth


def get_depth_tree(uids: list[str]) -> dict[str, int]:
    """Get edition tree json and convert it into dict of all heading uids and their depth"""
    depths: dict[str, int] = {}

    for uid in uids:
        response = requests.get(TREE_URL.format(uid=uid))
        response.raise_for_status()
        tree: list[dict] = response.json()[uid]
        get_depths(tree, depths, initial_depth=1)

    return depths


def get_mainmatter_preheadings(edition_id: str, uids: list[str]) -> VolumePreheadings:
    all_matters_preheadings = VolumePreheadings()

    for uid in uids:
        response = requests.get(API_URL + API_ENDPOINTS["edition_mainmatter"].format(edition_id=edition_id, uid=uid))
        response.raise_for_status()
        nodes = response.json()

        full_mainmatter_preheadings = (
            MainMatterPreheadings()
        )  # a collection of headings for a whole mainmatter (single uid)
        single_leaf_preheadings = PreheadingsGroup()  # a collection of headings to put before each "leaf"

        for node in nodes[1:]:  # we want to skip the uid's preheading (e.g. mn)
            if node["type"] == "branch":
                single_leaf_preheadings.append(Preheading.parse_obj(node))
            elif node["type"] == "leaf" and single_leaf_preheadings:
                # reached the end of preheadings for one mainmatter
                # copy the list for that mainmatter to a higher order container (with all mainmatters per uid)
                full_mainmatter_preheadings.append(deepcopy(single_leaf_preheadings))
                # and reset the list - start new collection for another mainmatter
                single_leaf_preheadings.clear()
            else:
                continue  # nothing to reset, nothing to add. Continue

        all_matters_preheadings.append(deepcopy(full_mainmatter_preheadings))

    return all_matters_preheadings


def get_mainmatters_headings_ids(edition_id: str, uids: list[str]) -> VolumeHeadings:
    """Only collects headings ids as the titles may be out of sync with the publication content"""
    all_matters_headings = VolumeHeadings()

    for uid in uids:
        response = requests.get(API_URL + API_ENDPOINTS["edition_mainmatter"].format(edition_id=edition_id, uid=uid))
        response.raise_for_status()
        nodes = response.json()

        full_mainmatter_headings = MainMatterHeadings()
        leaves_group = HeadingsGroup()

        for node in nodes:
            if node["type"] == "leaf":
                leaves_group.append(Heading.parse_obj(node))
            elif node["type"] == "branch" and leaves_group:
                full_mainmatter_headings.append(deepcopy(leaves_group))
                leaves_group = HeadingsGroup()
        else:
            full_mainmatter_headings.append(deepcopy(leaves_group))

        all_matters_headings.append(deepcopy(full_mainmatter_headings))

    return all_matters_headings


def get_extras_data(edition_id: str) -> dict:
    response = requests.get(API_URL + API_ENDPOINTS["edition_files"].format(edition_id=edition_id))
    response.raise_for_status()

    return dict(response.json())  # cast(dict, json.load(payload.decode('utf-8')))


def get_edition_data(edition_config: EditionConfig) -> EditionData:
    edition_data = EditionData()
    for _volume_details in edition_config.edition.volumes:
        _depth_tree = get_depth_tree(
            uids=_volume_details.mainmatter,
        )
        _preheadings = get_mainmatter_preheadings(
            edition_id=edition_config.edition.edition_id,
            uids=_volume_details.mainmatter,
        )
        _headings_ids = get_mainmatters_headings_ids(
            edition_id=edition_config.edition.edition_id,
            uids=_volume_details.mainmatter,
        )
        _mainmatter = get_mainmatter_data(
            edition_id=edition_config.edition.edition_id,
            uids=_volume_details.mainmatter,
        )
        _extras = get_extras_data(edition_id=edition_config.edition.edition_id)

        _acronym_response = requests.get(
            API_URL + API_ENDPOINTS["config_with_acronym"].format(uid=_volume_details.mainmatter[0])
        )
        _acronym_response.raise_for_status()
        _acronym = _acronym_response.json()[0]["acronym"]

        edition_data.append(
            VolumeData(
                preheadings=_preheadings,
                headings=_headings_ids,
                mainmatter=_mainmatter,
                extras=_extras,
                acronym=_acronym,
                depth_tree=_depth_tree,
            )
        )
    return edition_data
