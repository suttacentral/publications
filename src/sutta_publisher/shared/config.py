from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

import inject
import requests

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.publishers.html import HtmlPublisher


@dataclass(frozen=True)
class EditionsConfig:
    publication_number: str
    text_uid: str
    edition_number: str
    isbn: str
    cip: str
    publication_type: str
    format: str
    creator: str
    output: str
    page_size: str
    cover_image: str
    main_toc_depth: str
    secondary_toc: bool
    number_of_volumes: int
    volumes: list


@dataclass(frozen=True)
class Config:
    publication_number: str
    root_title: str
    creator_name: str
    translation_title: str
    translation_subtitle: str
    editions: list(EditionsConfig)

    _PUBLICATION_JSON_RAW_URL = (
        "https://raw.githubusercontent.com/suttacentral/bilara-data/published/_publication-v2.json"
    )

    @classmethod
    def from_publication(cls, publication_number: str) -> Config:

        try:
            publication_details = cls._get_publication_details(publication_number)
        except StopIteration as err:
            raise ValueError(f"Publication {publication_number} does not exist") from err

        edition = cls._get_edition_for_publication(publication_details)

        publication_details["editions"] = edition

        return cls(**publication_details)

    @classmethod
    def _get_publication_details(cls, publication_number: str) -> dict:
        response = requests.get(cls._PUBLICATION_JSON_RAW_URL)
        response.raise_for_status()

        publications: dict = response.json()
        publication_details: dict = next(
            item for item in publications if item["publication_number"] == publication_number
        )

        return publication_details

    @classmethod
    def _get_edition_for_publication(cls, publication: dict) -> dict:
        """
        Function to be updated when editions files will be uploaded to bilara-data repo
        """

        """
        response = requests.get(publication.get("editions_url"))
        response.raise_for_status()
        edition = response.json()
        return edition
        """

        # Dummy return vaule
        return {"key1": "val1", "key2": "val1", "key3": "val1", "key4": {"key1": "val1", "key2": "val"}}


def setup_logging() -> None:
    log_format = "[%(levelname)7s] %(filename)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")


def setup_inject(publication_number: str, bindings: dict = None) -> None:
    """Setup configuration for the application."""
    bindings = bindings or {}
    actual_bindings = {
        Config: Config.from_publication(publication_number=publication_number),
        ActivePublishers: ActivePublishers([HtmlPublisher()]),
    }

    def conf_callback(binder: inject.Binder) -> None:
        actual_bindings.update(cast(dict, bindings))
        [binder.bind(*args) for args in actual_bindings.items()]

    inject.clear_and_configure(conf_callback)
