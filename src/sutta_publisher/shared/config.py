from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

import requests
from pydantic import ValidationError

from sutta_publisher.shared.value_objects.edition_config import EditionConfig, EditionMappingList, EditionsConfigs

PAYLOADS_PATH = Path(__file__).parent / "example_payloads"
API_URL = "http://localhost:80/api/"  # TODO: Change url for real one
API_ENDPOINTS = {
    "editions_mapping": "publication/editions",
    "specific_edition": "publication/edition/{edition_id}",
}


def get_editions_ids(publication_number: str) -> list[str]:
    """Get the editions that are for given `publication_number`."""
    response = requests.get(API_URL + API_ENDPOINTS["editions_mapping"])
    response.raise_for_status()
    payload = response.content

    editions = EditionMappingList.parse_raw(payload)
    return cast(list[str], editions.get_editions_id(publication_number=publication_number))


def get_edition_config(edition_id: str) -> EditionConfig:
    """Fetch config for a given edition."""
    response = requests.get(API_URL + API_ENDPOINTS["specific_edition"].format(edition_id=edition_id))
    response.raise_for_status()
    payload = response.content.decode("utf-8")

    config = EditionConfig.parse_raw(payload)
    return config


def get_editions_configs(publication_number: str) -> EditionsConfigs:
    """Build a list of available editions config."""
    editions_id: list[str] = get_editions_ids(publication_number=publication_number)

    editions_config = EditionsConfigs()
    for each_id in editions_id:
        try:
            editions_config.append(get_edition_config(edition_id=each_id))
        except ValidationError:
            logging.warning("Not upported edition type found. Skipping to next one.")

    if not editions_config:
        raise SystemExit(f"No valid edition configs found for {publication_number=}. Stopping.")
    return editions_config


def setup_logging() -> None:
    log_format = "[%(levelname)7s] %(filename)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
