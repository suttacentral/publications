from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

from sutta_publisher.shared.value_objects.edition_config import EditionConfig, EditionMappingList, EditionsConfigs

PAYLOADS_PATH = Path(__file__).parent / "example_payloads"


def get_editions_ids(publication_number: str) -> list[str]:
    """Get the editions that are for given `publication_number`."""
    # TODO: [#20] Get data from real api
    f_path = PAYLOADS_PATH / "publication_editions_mapping.json"
    with open(f_path) as f:
        payload = f.read()
    editions = EditionMappingList.parse_raw(payload)
    return cast(list[str], editions.get_editions_id(publication_number=publication_number))


def get_edition_config(edition_id: str) -> EditionConfig:
    """Fetch config for a given edition."""
    # TODO: [#20] Get data from real api
    f_path = PAYLOADS_PATH / f"{edition_id}.json"
    with open(f_path) as f:
        payload = f.read()
    config = EditionConfig.parse_raw(payload)
    return config


def get_editions_configs(publication_number: str) -> EditionsConfigs:
    """Build a list of available editions config."""
    editions_id: list[str] = get_editions_ids(publication_number=publication_number)

    editions_config = EditionsConfigs()
    for each_id in editions_id:
        try:
            editions_config.append(get_edition_config(edition_id=each_id))
        except FileNotFoundError:
            msg = "No edition config found for edition_id=%s, skipping that edition."
            logging.warning(msg, each_id)

    if not editions_config:
        raise SystemExit(f"No valid edition configs found for {publication_number=}. Stopping.")
    return editions_config


def setup_logging() -> None:
    log_format = "[%(levelname)7s] %(filename)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")
