from __future__ import annotations

from typing import NoReturn

import requests

from sutta_publisher.shared import API_ENDPOINTS, API_URL, SUPER_TREE_URL, TREE_URL
from sutta_publisher.shared.value_objects.edition_config import EditionConfig, Volumes
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, MainMatterPart, VolumeData


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


def get_text_type(text_uid: str, super_tree: list[dict]) -> str | NoReturn:
    """Get type of given text"""
    for item in super_tree:
        if f"'{text_uid}'" in str(item):
            text_type: str = list(item.keys())[0]
            return text_type

    # If uid not found, we stop the app as we cannot get the structure tree
    raise SystemExit(f"Publication '{text_uid}' type not found in super_tree.json")


def get_depths(tree: list[dict | str], depths: dict[str, int], initial_depth: int = 1) -> None:
    """Get all headings depth recursively"""
    for item in tree:
        if isinstance(item, dict):
            depths[list(item.keys())[0]] = initial_depth
            _tree = list(item.values())[0]
            get_depths(_tree, depths, initial_depth=initial_depth + 1)
        elif isinstance(item, str):
            depths[item] = initial_depth


def _get_volume_tree(tree: list[dict], uid: str) -> list[dict] | None:
    for item in tree:
        if uid in item:
            return [item]
        elif isinstance(item, dict):
            _tree = _get_volume_tree(tree=list(item.values())[0], uid=uid)
            if _tree:
                return _tree
    return None


def get_extras_data(edition_id: str) -> dict:
    response = requests.get(API_URL + API_ENDPOINTS["edition_files"].format(edition_id=edition_id))
    response.raise_for_status()

    return dict(response.json())  # cast(dict, json.load(payload.decode('utf-8')))


def get_tree(uid: str, tree: list[dict]) -> dict | str | None:
    for item in tree:
        if item == uid:
            return item
        elif isinstance(item, dict):
            if list(item.keys())[0] == uid:
                return item
            elif _item := get_tree(uid=uid, tree=list(item.values())[0]):
                return _item
    return None


def get_edition_tree(text_uid: str, volumes: Volumes) -> list[list[dict | str]]:
    edition_tree = []

    _super_tree_response = requests.get(SUPER_TREE_URL)
    _super_tree_response.raise_for_status()
    _super_tree: list[dict] = _super_tree_response.json()

    _text_type: str = get_text_type(text_uid=text_uid, super_tree=_super_tree)
    _edition_super_tree: dict | str = get_tree(uid=text_uid, tree=_super_tree)  # type: ignore

    _temp_tree: list[dict] = []

    if isinstance(_edition_super_tree, str):
        _url = TREE_URL.format(text_type=_text_type, tree_uid=_edition_super_tree)
        _tree_response = requests.get(_url)
        _tree_response.raise_for_status()
        _temp_tree.append(_tree_response.json())

    else:
        for tree_uid in _edition_super_tree[text_uid]:
            _url = TREE_URL.format(text_type=_text_type, tree_uid=tree_uid)
            _tree_response = requests.get(_url)
            _tree_response.raise_for_status()
            _temp_tree.append(_tree_response.json())

    _edition_uids: list[list[str]] = [_volume.mainmatter for _volume in volumes]

    if len(volumes) == 1 and len(_edition_uids[0]) == 1:
        edition_tree.append(list(_temp_tree[0].values())[0])
    else:
        for _volume_uids in _edition_uids:
            edition_tree.append([get_tree(uid=_uid, tree=_temp_tree) for _uid in _volume_uids])

    return edition_tree


def get_edition_data(edition_config: EditionConfig) -> EditionData:
    edition_data = EditionData()
    _text_uid: str = edition_config.edition.text_uid
    _edition_tree: list[list[dict | str]] = get_edition_tree(
        text_uid=_text_uid,
        volumes=edition_config.edition.volumes,
    )

    for _volume_index, _volume_details in enumerate(edition_config.edition.volumes):
        _mainmatter = get_mainmatter_data(
            edition_id=edition_config.edition.edition_id,
            uids=_volume_details.mainmatter,
        )
        _extras = get_extras_data(edition_id=edition_config.edition.edition_id)

        _depths: dict[str, int] = {}
        get_depths(tree=_edition_tree[_volume_index], depths=_depths)

        edition_data.append(
            VolumeData(
                mainmatter=_mainmatter,
                extras=_extras,
                tree=_edition_tree[_volume_index],
                depths=_depths,
            )
        )
    return edition_data
