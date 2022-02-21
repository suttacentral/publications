from __future__ import annotations

import logging
from abc import ABC
from typing import Type

from sutta_publisher.edition_parsers.helper_functions import _fetch_possible_refs, _process_a_line
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
        self.possible_refs = _fetch_possible_refs()

    def __generate_html(self) -> str:
        """Generate content of an HTML body"""
        log.info("Generating html...")
        html_output: list[str] = []
        for volume in self.raw_data:  # iterate over volumes
            volume_html: list[str] = []
            for volume_content in volume.mainmatter:  # iterate over matters in each volume
                volume_text: dict[str, str] = volume_content.mainmatter.main_text
                markup: dict[str, str] = volume_content.mainmatter.markup
                reference: dict[str, str] = volume_content.mainmatter.reference
                for segment_id, text in volume_text.items():
                    references_per_segment_id = reference[segment_id].split(", ")
                    volume_html.append(
                        _process_a_line(
                            markup=markup[segment_id],
                            segment_id=segment_id,
                            text=text,
                            references=references_per_segment_id,
                            possible_refs=self.possible_refs,
                        )
                    )
            html_output.append("".join(volume_html))
        return "".join(html_output)

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
