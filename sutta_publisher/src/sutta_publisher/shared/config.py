from __future__ import annotations

import ast
import logging
import os

import requests
from pydantic import ValidationError

from sutta_publisher.shared.value_objects.edition_config import EditionConfig, EditionMappingList, EditionsConfigs

API_URL = os.getenv("API_URL", "")
API_ENDPOINTS = ast.literal_eval(os.getenv("API_ENDPOINTS", ""))
CREATOR_BIOS_URL = os.getenv("CREATOR_BIOS_URL", "")


def get_editions_ids(publication_number: str) -> list[str]:
    """Get the editions that are for given `publication_number`."""
    response = requests.get(API_URL + API_ENDPOINTS["editions_mapping"])
    response.raise_for_status()
    payload = response.content

    editions = EditionMappingList.parse_raw(payload)
    return editions.get_editions_id(publication_number=publication_number)  # type: ignore


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

    return config


def get_editions_configs(publication_number: str) -> EditionsConfigs:
    """Build a list of available editions config."""
    editions_id: list[str] = get_editions_ids(publication_number=publication_number)

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
        raise SystemExit(f"No valid edition configs found for {publication_number=}. Stopping.")
    return editions_config


def setup_logging() -> None:
    log_format = "[%(levelname)7s] %(filename)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
