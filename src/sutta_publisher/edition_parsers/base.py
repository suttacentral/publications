from __future__ import annotations

import logging
from abc import ABC
from typing import Type

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData

log = logging.getLogger(__name__)


class EditionParser(ABC):
    config: EditionConfig
    raw_data: EditionData
    edition_type: EditionType

    def __init__(self, config: EditionConfig, data: EditionData) -> None:
        self.raw_data = data
        self.config = config

    def __generate_html(self) -> None:
        log.info("Generating html...")

    def __generate_covers(self) -> None:
        log.info("Generating covers...")

    def __generate_frontmatter(self) -> None:
        log.info("Generating front matters...")

    def __generate_endmatter(self) -> None:
        log.info("Generating end matters...")

    def collect_all(self) -> EditionResult:
        self.__generate_html()
        self.__generate_frontmatter()
        self.__generate_endmatter()
        self.__generate_covers()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result

    @classmethod
    def get_edition_mapping(cls) -> dict[EditionType, Type[EditionParser]]:
        return {klass.edition_type: klass for klass in cls.__subclasses__()}
