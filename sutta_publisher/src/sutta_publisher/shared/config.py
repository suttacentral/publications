from __future__ import annotations

import logging

import requests
from pydantic import ValidationError

from sutta_publisher.shared import API_ENDPOINTS, API_URL, CREATOR_BIOS_URL
from sutta_publisher.shared.value_objects.edition_config import EditionConfig, EditionMappingList, EditionsConfigs


def get_edition_ids(publication_numbers: str) -> list[str]:
    """Get the editions that are for given `publication_numbers`."""
    response = requests.get(API_URL + API_ENDPOINTS["editions_mapping"])
    response.raise_for_status()
    payload = response.content

    editions: EditionMappingList = EditionMappingList.parse_raw(payload)

    if publication_numbers:
        _publication_numbers = publication_numbers.split(",")
        edition_ids: list[str] = editions.get_edition_ids(publication_numbers=_publication_numbers)
    else:
        edition_ids = editions.auto_find_edition_ids()

    return edition_ids


def get_edition_config(edition_id: str) -> EditionConfig:
    """Fetch config for a given edition."""
    response = requests.get(API_URL + API_ENDPOINTS["specific_edition"].format(edition_id=edition_id))
    response.raise_for_status()
    payload = response.content.decode("utf-8")

    config = EditionConfig.parse_raw(payload)

    # We need to set creator_bio separately as it comes from a different source
    bios_response = requests.get(CREATOR_BIOS_URL)
    bios_response.raise_for_status()
    creators_bios: list[dict[str, str]] = bios_response.json()
    try:
        (target_bio,) = [bio for bio in creators_bios if bio["creator_uid"] == config.publication.creator_uid]
        config.publication.creator_bio = target_bio["creator_biography"]
    except ValueError:
        raise SystemExit(f"No creator's biography found for: {config.publication.creator_uid}. Stopping.")

    config.publication.creator_bio = target_bio["creator_biography"]

    return config


def get_edition_configs(publication_numbers: str) -> EditionsConfigs:
    """Build a list of available editions config."""
    editions_id: list[str] = get_edition_ids(publication_numbers=publication_numbers)

    editions_config = EditionsConfigs()
    for each_id in editions_id:
        try:
            editions_config.append(get_edition_config(edition_id=each_id))
        except ValidationError as err:
            messages = ["Unsupported edition type found. Skipping to next one. Details:"]
            for idx, error in enumerate(err.errors()):
                error_location = " -> ".join(str(module) for module in error["loc"])
                messages.append(f'[{idx+1}] {error_location}: {error["msg"]} ({error["type"]})')
            logging.warning(" ".join(messages))

    if not editions_config:
        raise SystemExit(f"No valid edition configs found for {publication_numbers=}. Stopping.")
    return editions_config


def setup_logging() -> None:
    log_format = "[%(levelname)7s] %(filename)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
