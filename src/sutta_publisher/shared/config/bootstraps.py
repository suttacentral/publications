from __future__ import annotations

import logging
from typing import cast

import inject

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.publishers.html import HtmlPublisher

from .app_config import Config


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
