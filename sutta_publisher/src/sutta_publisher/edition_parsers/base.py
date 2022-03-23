from __future__ import annotations

import ast
import logging
from abc import ABC
from typing import Type

import requests
from bs4 import BeautifulSoup, Tag

from sutta_publisher.edition_parsers.helper_functions import (
    MAX_HEADING_DEPTH,
    _collect_headings,
    _fetch_possible_refs,
    _process_a_line,
    collect_main_toc_depths,
)
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData

log = logging.getLogger(__name__)


class EditionParser(ABC):
    config: EditionConfig
    raw_data: EditionData
    edition_type: EditionType

    def __init__(self, config: EditionConfig, data: EditionData) -> None:
        self.raw_data: EditionData = data
        self.config: EditionConfig = config
        self.possible_refs: list[str] = _fetch_possible_refs()
        self.per_volume_html: list[BeautifulSoup] = EditionParser.__generate_html(
            raw_data=data, possible_refs=self.possible_refs
        )

    @staticmethod
    def __generate_html(raw_data: EditionData, possible_refs: list[str]) -> list[BeautifulSoup]:
        """Generate content of an HTML body"""
        log.debug("Generating html...")

        # Publication is separated into volumes
        publication_html_volumes_output: list[str] = []
        for volume in raw_data:
            # Each volume's mainmatter is separated into a list of mainmatter sub-entities (MainMatterDetails class)
            processed_single_mainmatter_subentity: list[str] = []
            for mainmatter_info in volume.mainmatter:
                processed_mainmatter_single_lines: list[str] = []
                try:
                    # Only store segment_id if it has matching text (prune empty strings: "")
                    segment_ids = [segment_id for segment_id, _ in mainmatter_info.mainmatter.markup.items()]

                    # Each mainmatter sub-entity (MainMatterDetails) have dictionaries with text lines, markup lines and references. Keys are always segment IDs
                    for segment_id in segment_ids:
                        processed_mainmatter_single_lines.append(
                            _process_a_line(
                                markup=mainmatter_info.mainmatter.markup.get(segment_id),
                                segment_id=segment_id,
                                text=mainmatter_info.mainmatter.main_text.get(segment_id, ""),
                                references=mainmatter_info.mainmatter.reference.get(segment_id, ""),
                                # references are provides as: "single, comma, separated, string". We take care of splitting it in helper functions
                                possible_refs=possible_refs,
                            )
                        )
                except AttributeError:
                    # 'NoneType' object has no attribute 'keys' -- means the mainmatter is an empty dict. Skip it.
                    continue

                single_mainmatter_subentity_output: str = "".join(
                    processed_mainmatter_single_lines
                )  # putting one sub-entity together (complete HTML body)
                processed_single_mainmatter_subentity.append(
                    single_mainmatter_subentity_output
                )  # collecting sub-entities into one full mainmatter of a volume
            single_mainmatter_output: str = "".join(
                processed_single_mainmatter_subentity
            )  # a complete mainmatter of a single volume in HTML <body>{single_mainmatter_output}</body>
            publication_html_volumes_output.append(
                single_mainmatter_output
            )  # all main matters from each volumes as a list of html bodies' contents
        return [BeautifulSoup(volume, "lxml") for volume in publication_html_volumes_output]

    def __collect_main_toc_headings(self) -> None:
        log.debug("Collecting headings for the main ToC...")
        depth: str = self.config.edition.main_toc_depth
        per_volume_depth: list[int] = collect_main_toc_depths(depth=depth, all_volumes=self.per_volume_html)
        self.main_toc_headings: list[list[Tag]] = []
        for depth_, volume_ in zip(per_volume_depth, self.per_volume_html):
            self.main_toc_headings.append(_collect_headings(end_depth=depth_, volume=volume_))

    def __collect_secondary_toc_targets(self) -> list[Tag]:
        # TODO: implement
        pass

    def __collect_secondary_toc_headings(self) -> None:
        log.debug("Collecting headings for secondary ToCs...")
        depth: str = self.config.edition.main_toc_depth
        per_volume_targets = self.__collect_secondary_toc_targets()
        per_volume_depth: list[int] = []
        for i in collect_main_toc_depths(depth=depth, all_volumes=self.per_volume_html):
            per_volume_depth.append(i + 1 if i < MAX_HEADING_DEPTH else i)  # to avoid having start_depth > end_depth
        self.secondary_toc_headings: dict[Tag, list[Tag]] = {}
        for target_, depth_, volume_ in zip(per_volume_targets, per_volume_depth, self.per_volume_html):
            self.secondary_toc_headings.update(
                {target_: _collect_headings(start_depth=depth_, end_depth=MAX_HEADING_DEPTH, volume=volume_)}
            )

    def __generate_toc(self) -> None:
        self.__collect_main_toc_headings()
        if self.config.edition.secondary_toc:
            self.__collect_secondary_toc_headings()

    def __generate_frontmatter(self) -> dict[str, str]:
        log.debug("Generating covers...")
        frontmatter = ast.literal_eval(self.config.edition.volumes.json())[0].get("frontmatter")
        working_dir = self.config.edition.working_dir.removeprefix("/opt/sc/sc-flask/sc-data")

        # TODO: move to .env
        url = (
            "https://raw.githubusercontent.com/suttacentral/sc-data/master" + "{working_dir}" + "{matter}"
        )  # Don't worry it will be moved to .env, it's covered by another ticket ;)

        matter_paths = [elem.removeprefix(".") for elem in frontmatter if elem.startswith("./")]

        matters_dict = dict()

        for suffix in matter_paths:
            response = requests.get(url.format(matter=suffix, working_dir=working_dir))
            response.raise_for_status()

            match suffix:
                case "/matter/foreword.html":
                    matters_dict["foreword"] = response.text

                case "/matter/introduction.html":
                    matters_dict["introduction"] = response.text

                case "/matter/acknowledgements.html":
                    matters_dict["acknowledgements"] = response.text

                case _:
                    # raise ValueError("Not supported frontmatter type")
                    pass

        return matters_dict

    def __generate_covers(self) -> None:
        log.debug("Generating covers...")

    def __generate_endmatter(self) -> None:
        log.debug("Generating end matters...")

    def collect_all(self) -> EditionResult:
        self.__generate_html(raw_data=self.raw_data, possible_refs=self.possible_refs)
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
