from __future__ import annotations

import ast
import logging
import os
import re
from abc import ABC
from copy import deepcopy
from typing import Type

import requests
from bs4 import BeautifulSoup, Tag

from sutta_publisher.edition_parsers.helper_functions import (
    add_class,
    collect_actual_headings,
    collect_main_toc_depths,
    collect_secondary_toc_depths,
    create_html_heading_with_id,
    fetch_possible_refs,
    find_all_headings,
    find_children_by_index,
    find_sutta_title_depth,
    get_heading_depth,
    increment_heading_by_number,
    make_headings_tree,
    process_a_line,
    remove_all_ul,
)
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData

log = logging.getLogger(__name__)


class EditionParser(ABC):
    FRONTMATTER_URL = os.getenv("FRONTMATTER_URL", "")

    config: EditionConfig
    raw_data: EditionData
    edition_type: EditionType

    def __init__(self, config: EditionConfig, data: EditionData) -> None:
        # Order of execution matters a great deal here as functions depends on instance fields being initialised upon their call.
        self.raw_data: EditionData = data
        self.config: EditionConfig = config
        self.possible_refs: list[str] = fetch_possible_refs()
        self.per_volume_html: list[BeautifulSoup] = self.__generate_html()
        self.mainmatter_postprocess()
        self.frontmatters: list[dict[str, BeautifulSoup | list[list[Tag]]]] = self.generate_frontmatter()

    def __generate_html(self) -> list[BeautifulSoup]:
        """Generate content of an HTML body"""
        log.debug("Generating html...")

        # Publication is separated into volumes
        publication_html_volumes_output: list[str] = []
        for volume in self.raw_data:
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
                            process_a_line(
                                markup=mainmatter_info.mainmatter.markup.get(segment_id),
                                segment_id=segment_id,
                                text=mainmatter_info.mainmatter.main_text.get(segment_id, ""),
                                references=mainmatter_info.mainmatter.reference.get(segment_id, ""),
                                # references are provides as: "single, comma, separated, string". We take care of splitting it in helper functions
                                possible_refs=self.possible_refs,
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

        volumes = [BeautifulSoup(volume, "lxml") for volume in publication_html_volumes_output]

        return volumes

    def __collect_preheading_insertion_targets(self) -> list[Tag]:
        targets: list[Tag] = []

        for volume_headings, volume_html in zip(self.raw_data, self.per_volume_html):
            for mainmatter_headings in volume_headings.headings:
                for headings_group in mainmatter_headings:
                    for heading in headings_group:
                        targets.append(volume_html.find(id=heading.uid))

        return targets

    def mainmatter_postprocess(self) -> None:
        """Apply some additional postprocessing steps and insert additional headings to the generated crude mainmatters"""

        # Remove all <ul></ul> tags
        for html in self.per_volume_html:
            remove_all_ul(html=html)

        # Change numbers of all headings according to how many additional preheadings are. If there are 2 preheadings h1's become h3's
        for volume, html in zip(self.raw_data, self.per_volume_html):
            additional_depth = len(volume.preheadings[0][0])
            for heading in find_all_headings(html):
                increment_heading_by_number(by_number=additional_depth, heading=heading)

        # Insert preheadings
        for volume, html in zip(self.raw_data, self.per_volume_html):
            for mainmainmatter_preheadings, mainmainmatter_headings in zip(volume.preheadings, volume.headings):
                for preheading_group, heading_group in zip(mainmainmatter_preheadings, mainmainmatter_headings):

                    target = html.find(id=heading_group[0].heading_id)

                    for level, preheading in enumerate(preheading_group):
                        # Why this crazy logic?
                        # 1. +1: because list enumeration is 0-based (1, 2, 3, ...) and HTML headings are 1-based (h1, h2, h3, ...)
                        # 2. len(volume.preheadings[0][0]) - len(preheading_group): because preheadings tree looks like this
                        #      [main preheadings group] - main preheading                                              (h1)
                        #      [main preheadings group]    - another preheading, before each group of suttas           (h2)
                        #      [main preheadings group]        - yet another preheading, before each group of suttas   (h3)
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - (...)                                          (h4 class="sutta-title")
                        # [secondary preheadings group] - another preheading, before each group of suttas              (h2)
                        # [secondary preheadings group]        - yet another preheading, before each group of suttas   (h3)
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - (...)                                          (h4 class="sutta-title")
                        #      [main preheadings group] - main preheading                                              (h1)
                        #      [main preheadings group]    - another preheading, before each group of suttas           (h2)
                        #      [main preheadings group]        - yet another preheading, before each group of suttas   (h3)
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - sutta                                          (h4 class="sutta-title")
                        #                                             - (...)                                          (h4 class="sutta-title")
                        # DEPTH OF PREHEADINGS VARIES! (not only between publications but between parts of a single publication)
                        main_preheadings_depth = len(volume.preheadings[0][0])
                        secondary_preheadings_depth = len(preheading_group)
                        _level = level + 1 + main_preheadings_depth - secondary_preheadings_depth

                        target.insert_before(
                            create_html_heading_with_id(
                                html=html, depth=_level, text=preheading.name, id=preheading.uid
                            )
                        )

        # Add class "heading" for all HTML headings between h1 and hX which has class "sutta-title"
        for html in self.per_volume_html:
            depth = find_sutta_title_depth(html)
            headings = collect_actual_headings(end_depth=depth, volume=html)

            add_class(tags=headings, class_="heading")

        # Add class "subheading" for all HTML headings below hX with class "sutta-title"
        for html in self.per_volume_html:
            start_depth = find_sutta_title_depth(html) + 1
            headings = collect_actual_headings(start_depth=start_depth, end_depth=999, volume=html)

            add_class(tags=headings, class_="subheading")

    def collect_main_toc_headings(self) -> list[list[Tag]]:
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
            main_toc_headings.append(collect_actual_headings(end_depth=_depth, volume=_volume))

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
            toc_targets.append(collect_actual_headings(start_depth=_depth, end_depth=_depth, volume=_volume))
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
        per_volume_depths: list[tuple[int, int]] = collect_secondary_toc_depths(
            main_toc_depths=main_toc_depths, all_volumes=self.per_volume_html
        )

        all_volumes_tocs: list[dict[Tag, list[Tag]]] = []
        for _targets, _depth, _volume in zip(per_volume_targets, per_volume_depths, self.per_volume_html):
            secondary_toc_headings: dict[
                Tag, list[Tag]
            ] = {}  # mapping is reset for each volume. We deepcopy it to a list with all volumes
            # In each volume matching the right parent heading with its deeper level headings/children is important. After all these children will create secondary ToC and the parent will be a target for it's insertion
            tree = make_headings_tree(
                headings=collect_actual_headings(start_depth=_depth[0] - 1, end_depth=_depth[1], volume=_volume)
            )
            parents = [
                (index, heading) for (index, heading) in tree.items() if get_heading_depth(heading) == _depth[0]
            ]  # parents (targets) are all highest level headings from this collection

            # We got indexed headings and filtered out (indexed) parents, so all there is to do is find parent's children by index and build a mapping for each volume
            for _index, _target in parents:
                secondary_toc_headings.update(
                    {
                        _target: [
                            tree[child_index]
                            for child_index in find_children_by_index(index=_index, headings_tree=tree)
                        ]
                    }
                )

            all_volumes_tocs.append(deepcopy(secondary_toc_headings))

        return all_volumes_tocs

    def generate_frontmatter(self) -> list[dict[str, BeautifulSoup | list[list[Tag]]]]:
        """Fetch a list of frontmatter components and their contents from API, return a dictionary with {<component_name>: <content>} mapping.
        The output is returned for each volume of a publication.
        """
        log.debug("Generating FrontMatters...")

        PREFIX = "/opt/sc/sc-flask/sc-data"

        per_volume_list: list[dict[str, BeautifulSoup | list[list[Tag]]]] = []

        # Parse list of frontmatters for this publication
        for volume, toc_headings in zip(
            ast.literal_eval(self.config.edition.volumes.json()), self.collect_main_toc_headings()
        ):

            frontmatter: list[str] = volume.get("frontmatter")
            working_dir: str = self.config.edition.working_dir.removeprefix(PREFIX)
            matter_paths = [elem.removeprefix(".") for elem in frontmatter if elem.startswith("./")]
            matters_dict: dict[str, BeautifulSoup | list[list[Tag]]] = {}

            for suffix in matter_paths:
                # Fetch actual frontmatters content from API
                response = requests.get(self.FRONTMATTER_URL.format(matter=suffix, working_dir=working_dir))
                response.raise_for_status()

                if match := re.search(r"^(/matter/)(?P<matter_name>\w+).html$", suffix):
                    matter = BeautifulSoup(response.text, "lxml")
                    remove_all_ul(matter)
                    matters_dict[match.group("matter_name")] = matter
                elif match := re.search(r"^(?P<titlepage>titlepage)$", suffix):
                    pass  # TODO [61]: implement collecting titlepage data
                elif match := re.search(r"^(?P<imprint>imprint)$", suffix):
                    pass  # TODO [61]: implement collecting imprint data
                elif match := re.search(r"^(?P<halftitlepage>halftitlepage)$", suffix):
                    pass  # TODO [61]: implement collecting halftitlepage data
                elif match := re.search(r"^(?P<main_toc>main-toc)$", suffix):
                    matters_dict[match.group("main-toc")] = toc_headings
                elif match := re.search(r"^(?P<blurbs>blurbs)$", suffix):
                    pass  # TODO [61]: implement collecting blurbs data

            per_volume_list.append(matters_dict)
        return per_volume_list

    def __generate_covers(self) -> None:
        log.debug("Generating covers...")

    def __generate_backmatter(self) -> None:
        log.debug("Generating back matters...")

    def collect_all(self) -> EditionResult:
        # self.__generate_html(raw_data=self.raw_data, possible_refs=self.possible_refs)
        self.generate_frontmatter()
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
