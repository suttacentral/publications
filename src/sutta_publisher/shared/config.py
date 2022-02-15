from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import inject

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.publishers.html import HtmlPublisher


@dataclass(frozen=True)
class Config:
    bilara_data_url = "https://github.com/suttacentral/bilara-data"
    publication_number: str
    input_path: Path = Path(__file__).parent / "dn.tsv"

    @classmethod
    def from_publication(cls, publication_number: str) -> Config:
        return cls(publication_number=publication_number)


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
