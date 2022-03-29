from __future__ import annotations

import ast
import logging
from abc import ABC
from copy import deepcopy
from typing import Type

import requests
from bs4 import BeautifulSoup, Tag

from sutta_publisher.edition_parsers.helper_functions import (
    _collect_headings,
    _collect_secondary_toc_depths,
    _fetch_possible_refs,
    _find_children_by_index,
    _get_heading_depth,
    _process_a_line,
    collect_main_toc_depths,
    make_headings_tree,
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

    def __collect_main_toc_headings(self) -> list[list[Tag]]:
        """Collect all headings, which belong to main ToCs.

        The collection is divided by volume.

        Returns:
            list[list[Tag]]: Headings to be placed in main ToCs, delivered as a list for each volume
            e.g.: [ [some_heading_for_volume_1, other_heading_for_volume_1], [some_heading_for_volume_2, other_heading_for_volume_2] ]
        """
        log.debug("Collecting headings for the main ToCs...")

        per_volume_depth: list[int] = collect_main_toc_depths(
            depth=self.config.edition.main_toc_depth, all_volumes=self.per_volume_html
        )
        main_toc_headings: list[list[Tag]] = []
        for _depth, _volume in zip(per_volume_depth, self.per_volume_html):
            main_toc_headings.append(_collect_headings(end_depth=_depth, volume=_volume))

        return main_toc_headings

    def __collect_secondary_toc_targets(self, main_toc_depths: list[int]) -> list[list[Tag]]:
        """Collect list of targets (heading), under them secondary tables of contents will be inserted.

        Returns:
            list[list[Tag]]: A list of headings for each volume
        """
        log.debug("Collecting targets to insert secondary ToCs...")

        toc_targets: list[list[Tag]] = []
        # Headings are in lists within a main list. Different list for each volume
        for _depth, _volume in zip(main_toc_depths, self.per_volume_html):
            toc_targets.append(_collect_headings(start_depth=_depth, end_depth=_depth, volume=_volume))
        return toc_targets

    def __collect_secondary_toc(self) -> list[dict[Tag, list[Tag]]]:
        """Based on main ToC headings generate a collection secondary ToCs headings for each volume

        Returns:
            list[dict[Tag, list[Tag]]]: for each volume a separate mapping is created. List of mappings for all volumes is returned. Mapping associates a heading in text where secondary ToC needs to be inserted with a list of headings required to build this ToC.
        """
        log.debug("Collecting headings for secondary ToCs...")

        main_toc_depths: list[int] = collect_main_toc_depths(
            depth=self.config.edition.main_toc_depth, all_volumes=self.per_volume_html
        )
        per_volume_targets = self.__collect_secondary_toc_targets(main_toc_depths)
        per_volume_depths: list[tuple[int, int]] = _collect_secondary_toc_depths(
            main_toc_depths=main_toc_depths, all_volumes=self.per_volume_html
        )

        all_volumes_tocs: list[dict[Tag, list[Tag]]] = []
        for _targets, _depth, _volume in zip(per_volume_targets, per_volume_depths, self.per_volume_html):
            secondary_toc_headings: dict[
                Tag, list[Tag]
            ] = {}  # mapping is reset for each volume. We deepcopy it to a list with all volumes
            # In each volume matching the right parent heading with its deeper level headings/children is important. After all these children will create secondary ToC and the parent will be a target for it's insertion
            tree = make_headings_tree(
                headings=_collect_headings(start_depth=_depth[0] - 1, end_depth=_depth[1], volume=_volume)
            )
            parents = [
                (index, heading) for (index, heading) in tree.items() if _get_heading_depth(heading) == _depth[0]
            ]  # parents (targets) are all highest level headings from this collection

            # We got indexed headings and filtered out (indexed) parents, so all there is to do is find parent's children by index and build a mapping for each volume
            for _index, _target in parents:
                secondary_toc_headings.update(
                    {
                        _target: [
                            tree[child_index]
                            for child_index in _find_children_by_index(index=_index, headings_tree=tree)
                        ]
                    }
                )

            all_volumes_tocs.append(deepcopy(secondary_toc_headings))

        return all_volumes_tocs

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

    def __generate_backmatter(self) -> None:
        log.debug("Generating end matters...")

    def collect_all(self) -> EditionResult:
        # self.__generate_html(raw_data=self.raw_data, possible_refs=self.possible_refs)
        self.__generate_frontmatter()
        self.__generate_backmatter()
        self.__generate_covers()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result

    @classmethod
    def get_edition_mapping(cls) -> dict[EditionType, Type[EditionParser]]:
        return {klass.edition_type: klass for klass in cls.__subclasses__()}
