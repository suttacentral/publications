from __future__ import annotations

import ast
import logging
import os
from abc import ABC
from copy import copy, deepcopy
from functools import cache
from pathlib import Path
from typing import Any, Callable, Type, cast

import jinja2
import requests
from bs4 import BeautifulSoup, Tag

from sutta_publisher.edition_parsers.helper_functions import (
    add_class,
    back_to_str,
    collect_actual_headings,
    collect_main_toc_depth,
    collect_secondary_toc_depth_range,
    create_html_heading_with_id,
    fetch_possible_refs,
    find_all_headings,
    find_children_by_index,
    find_sutta_title_depth,
    generate_html_toc,
    get_heading_depth,
    increment_heading_by_number,
    make_headings_tree,
    process_line,
    remove_all_ul, parse_main_toc_depth,
)
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig, VolumeDetail
from sutta_publisher.shared.value_objects.edition_data import EditionData, VolumeData, Node, MainMatter, MainMatterPart
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

log = logging.getLogger(__name__)


class EditionParser(ABC):
    HTML_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
    config: EditionConfig
    raw_data: EditionData
    edition_type: EditionType
    possible_refs: set[str]

    def __init__(self, config: EditionConfig, data: EditionData) -> None:
        self.raw_data: EditionData = data
        self.config: EditionConfig = config
        self.possible_refs: set[str] = fetch_possible_refs()

    def _create_edition_skeleton(self) -> Edition:
        """Creates a collection of empty volumes to work on."""
        # We need to set up volume numbers here to be able to match volume in raw data from API to output volume.
        # We need to be extra careful because:
        # (1) volume_number may be None so raw_data[volume_number] won't work
        # (2) volume_number is 1-based, whereas, raw_data is a list, so it has 0-based index
        if len(self.raw_data) == 1:  # means only 1 volume
            volumes = Volume(volume_number=None)
        else:
            volumes = [Volume(volume_number=num + 1) for num, _ in enumerate(self.raw_data)]
        return Edition(volumes=volumes)

    @staticmethod
    def _get_true_index(volume: Volume) -> int:
        """Get actual `volume`'s index (i.e. where it is
        in the volumes list of raw_data and volume-specific edition config)."""
        if volume.volume_number is None:
            return 0  # means there's only 1 volume, so index is 0
        else:
            # volume_number is 1-based index, whereas, lists have 0-based index
            return cast(int, volume.volume_number - 1)

    @staticmethod
    def _on_each_volume(edition: Edition, operation: Callable) -> None:
        """Loops over each volume in the `edition` and applies the `operation` to it."""
        [operation(volume) for volume in edition]

    def _collect_metadata(self, volume: Volume) -> dict[str, str | int | list[str]]:
        _index = EditionParser._get_true_index(volume)
        return {
            "acronym": self.raw_data[_index].acronym,
            "blurbs": self._get_blurbs_for_publication(),
            "created": self.config.edition.created,
            "creation_process": self.config.publication.creation_process,
            "creator_biography": self.config.publication.creator_bio,
            "creator_name": self.config.publication.creator_name,
            "edition_number": self.config.edition.edition_number,
            "editions_url": self.config.publication.editions_url,
            "first_published": self.config.publication.first_published,
            "number_of_volumes": len(self.raw_data),
            "publication_isbn": self.config.edition.publication_isbn,
            "publication_number": self.config.edition.publication_number,
            "publication_type": self.config.edition.publication_type.name,
            "root_name": self.config.publication.root_lang_name,
            "root_title": self.config.publication.root_title,
            "source_url": self.config.publication.source_url,
            "text_description": self.config.publication.text_description,
            "translation_name": self.config.publication.translation_lang_name,
            "translation_subtitle": self.config.publication.translation_subtitle,
            "translation_title": self.config.publication.translation_title,
            "updated": self.config.edition.updated,
            "volume_acronym": self.config.edition.volumes[_index].volume_acronym,
            "volume_isbn": self.config.edition.volumes[_index].volume_isbn,
            "volume_root_title": "",  # TODO[61]: implement - where do I get it from?
            "volume_translation_title": "",  # TODO[61]: implement - where do I get it from?
        }

    def set_metadata(self, volume: Volume) -> None:
        """Set fields with metadata in a `volume`. If attribute name is unknown
        (no such field in `Volume` definition) skip it."""
        _metadata = self._collect_metadata(volume)

        for _attr, _value in _metadata.items():
            try:
                setattr(volume, _attr, _value)
            except ValueError:
                continue

    def _generate_mainmatter(self, volume: Volume) -> str:
        # TODO: some ideas for further refactoring:
        #  - we check for segment_id-s without matching markup (with markup
        #       being empty string ("") or possibly None) - maybe this could be done by Pydantic?
        #       Not raise exception but ignore the key: value pairs with empty string as values.

        log.debug("Generating html...")

        # Structure of a volume's mainmatter needs some clarification, here's a structure tree:
        # mainmatter:
        #     - mainmatter_part1:
        #           - node1
        #               - texts1
        #               - markup1
        #               - references1
        #           - node2
        #               - texts2
        #               - markup2
        #               - references2
        #     - mainmatter_part2
        #           - node3
        #               - texts3
        #               - markup3
        #               - references3
        #           - node4
        #               - texts4
        #               - markup4
        #               - references4
        # In this schema lower level objects build higher level object,
        # so node1 is built of text1, markup1 and references1, mainmatter_part1 is built of node1 and node2 and so on...

        _index: int = EditionParser._get_true_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _mainmatter: str = self._process_mainmatter(_raw_data.mainmatter)

        _mainmatter = self._postprocess_mainmatter(_mainmatter, volume)

        return _mainmatter

    def _process_mainmatter(self, mainmatter: MainMatter) -> str:
        """Mainmatter may consist of several parts, deal with them separately and concatenate results into string."""
        return "".join([self._process_mainmatter_part(_part) for _part in mainmatter])

    def _process_mainmatter_part(self, part: MainMatterPart) -> str:
        """Part of mainmatter consists of nodes, deal with them separately and concatenate results into a string."""
        return "".join([self._process_mainmatter_node(_node) for _node in part])

    def _process_mainmatter_node(self, node: Node) -> str:
        """Parse a single 'node' from API and return a ready HTML string with several lines of mainmatter.

        Each node's content is split between dictionaries with lines of text, markup and references.
        Keys are always segment IDs.
        """
        _single_lines: list[str] = []

        # Some nodes are branches not leaves - they contain preheadings/headings but no mainmatter, we skip them.
        if not node.mainmatter:
            return ""

        else:
            # Only store segment_id if it has matching text (prune empty strings)
            _segment_ids: list[str] = [
                _id for _id, _markup in node.mainmatter.markup.items() if _markup
            ]  # type: ignore

            for _id in _segment_ids:
                _single_lines.append(
                    process_line(
                        markup=node.mainmatter.markup[_id],
                        segment_id=_id,
                        text=node.mainmatter.main_text.get(_id, ""),
                        references=node.mainmatter.reference.get(_id, ""),
                        possible_refs=self.possible_refs,
                    )
                )

            return "".join(_single_lines)  # putting content of one node together

    def _postprocess_mainmatter(self, mainmatter: str, volume: Volume) -> str:
        """Apply some additional postprocessing steps
        and insert additional headings to a crude mainmatter"""
        #TODO: this needs some refactoring but I have no idea how atm.

        _mainmatter: BeautifulSoup = BeautifulSoup(mainmatter, "lxml")
        _index: int = self._get_true_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]

        # Remove all <ul></ul> tags from <header></header> element
        remove_all_ul(html=_mainmatter.find("header"))

        # Change numbers of all headings according to how many additional preheadings are.
        # If there are 2 preheadings h1-s become h3-s.
        _additional_depth: int = len(_raw_data.preheadings[0][0])
        for heading in find_all_headings(_mainmatter):
            increment_heading_by_number(by_number=_additional_depth, heading=heading)

        # Insert preheadings
        for mainmatter_preheadings, mainmatter_headings in zip(_raw_data.preheadings, _raw_data.headings):
            for preheading_group, heading_group in zip(mainmatter_preheadings, mainmatter_headings):

                target: Tag = _mainmatter.find(id=heading_group[0].heading_id)

                for _level, _preheading in enumerate(preheading_group):
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
                    _main_depth: int = len(_raw_data.preheadings[0][0])
                    _secondary_depth: int = len(preheading_group)
                    _level = _level + 1 + _main_depth - _secondary_depth

                    target.insert_before(
                        create_html_heading_with_id(
                            html=_mainmatter, depth=_level, text=_preheading.name, id_=_preheading.uid
                        )
                    )

        # Add class "heading" for all HTML headings between h1 and hX which has class "sutta-title"
        _depth = find_sutta_title_depth(html=_mainmatter)
        _headings = collect_actual_headings(end_depth=_depth, html=_mainmatter)

        add_class(tags=_headings, class_="heading")

        # Add class "subheading" for all HTML headings below hX with class "sutta-title"
        _start_depth = find_sutta_title_depth(html=_mainmatter) + 1
        _subheadings = collect_actual_headings(start_depth=_start_depth, end_depth=999, html=_mainmatter)

        add_class(tags=_subheadings, class_="subheading")

        return cast(str, back_to_str(_mainmatter))

    def set_mainmatter(self, volume: Volume) -> None:
        _mainmatter = self._generate_mainmatter(volume)

        volume.mainmatter = _mainmatter

    def set_frontmatter(self, volume: Volume) -> None:
        pass

    def set_backmatter(self, volume: Volume) -> None:
        pass

    def set_filename(self, volume: Volume) -> None:
        _translation_title = volume.translation_title.replace(__old=" ", __new="-")
        _date = volume.updated if volume.updated else volume.created
        _date = _date.strftime("%Y-%m-%d")
        _volume_number = f"-{volume.volume_number}" if volume.volume_number else ""
        _file_extension = self.edition_type.name

        volume.filename = f"{_translation_title}-{volume.creator_uid}-{_date}{_volume_number}.{_file_extension}"

    def set_main_toc(self, volume: Volume) -> None:
        volume.main_toc = self._collect_main_toc_headings(volume)

    def set_secondary_toc(self, volume: Volume) -> None:
        pass

    # def _collect_preheading_insertion_targets(self, mainmatter: str, volume: Volume) -> list[Tag]:
    #     _targets: list[Tag] = []
    #
    #     _index: int = self._get_true_index(volume)
    #     _raw_data: VolumeData = self.raw_data[_index]
    #     _mainmatter = BeautifulSoup(mainmatter, "lxml")
    #
    #     for mainmatter_headings in _raw_data.headings:
    #         for headings_group in mainmatter_headings:
    #             for heading in headings_group:
    #                 _targets.append(_mainmatter.find(id=heading.heading_id))
    #
    #     return _targets

    def _collect_main_toc_headings(self, volume: Volume) -> list[Tag]:
        """Collect all headings, which belong to main ToCs.

        The collection is divided by volume.

        Returns:
            list[Tag]: Headings to be placed in main ToCs, delivered as a list of HTML tags
        """
        log.debug("Collecting headings for the main ToCs...")

        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        _depth: int = parse_main_toc_depth(
            depth=self.config.edition.main_toc_depth, html=_mainmatter
        )

        return cast(list[Tag], collect_actual_headings(end_depth=_depth, html=_mainmatter))

    @staticmethod
    def _collect_secondary_toc_targets(depth: int, html: BeautifulSoup) -> list[Tag]:
        """Collect list of targets, under which secondary tables of contents will be inserted.

        Returns:
            list[Tag]: A list of targets to insert secondary ToCs under.
        """
        log.debug("Collecting targets to insert secondary ToCs...")

        # Only collect deepest level of main ToC headings - they are targets for secondary ToCs
        return cast(list[Tag], collect_actual_headings(start_depth=depth, end_depth=depth, html=html))

    def _collect_secondary_toc(self, volume: Volume) -> dict[Tag, list[Tag]]:
        """Based on main ToC headings generate a collection secondary ToCs headings.

        Returns:
            dict[Tag, list[Tag]]: mapping associating headings in text where secondary ToCs needs to be inserted
                                  with a list of headings required to build this ToC.
        """
        log.debug("Collecting headings for secondary ToCs...")

        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        _main_toc_depth: int = parse_main_toc_depth(
            depth=self.config.edition.main_toc_depth, html=_mainmatter
        )
        _targets = EditionParser._collect_secondary_toc_targets(depth=_main_toc_depth, html=_mainmatter)
        _secondary_toc_depth: int = find_sutta_title_depth(html=_mainmatter)

        # for _targets, _depth, _volume in zip(_targets, _secondary_toc_depth, self.per_volume_html):
        secondary_toc_mapping: dict[
            Tag, list[Tag]
        ] = {}  # mapping is reset for each volume. We deepcopy it to a list with all volumes
        # Matching the right parent heading with its deeper level headings/children is important. After all these children will create secondary ToC and the parent will be a target for it's insertion

        _secondary_tocs_headings: list[Tag] = collect_actual_headings(start_depth=_main_toc_depth - 1, end_depth=_secondary_toc_depth, html=_mainmatter)

        tree = make_headings_tree(
            headings=_secondary_tocs_headings
        )
        parents = [
            (index, heading) for (index, heading) in tree.items() if get_heading_depth(heading) == _main_toc_depth
        ]  # parents (targets) are all highest level headings from this collection

        # We got indexed headings and filtered out (indexed) parents, so all there is to do is find parent's children by index and build a mapping
        for _index, _target in parents:
            secondary_toc_mapping.update(
                {
                    _target: [
                        tree[child_index]
                        for child_index in find_children_by_index(index=_index, headings_tree=tree)
                    ]
                }
            )

        return secondary_toc_mapping

    @cache
    def _get_blurbs_for_publication(self) -> list[str]:
        """Collect all blurbs across all volumes of a publication and return them as a flat list."""
        blurbs: list[str] = []

        for blurb in self.raw_data:
            blurbs.extend([node.blurb for node in blurb.mainmatter if node.blurb])

        return blurbs

    def _collect_matters(self, volume: Volume) -> dict[str, Any]:
        pass

    @staticmethod
    def _is_html_matter(matter: str) -> bool:
        return matter.startswith("./matter/")

    @staticmethod
    def _process_html_matter(matter: str, working_dir: str) -> str:
        matter = matter.removeprefix(".")

        if not (FRONTMATTER_URL := os.getenv("FRONTMATTER_URL")):
            log.error("Missing FRONTMATTER_URL, fix the .env_public file.")
            raise EnvironmentError("Missing FRONTMATTER_URL")
        else:
            response = requests.get(FRONTMATTER_URL.format(matter=matter, working_dir=working_dir))
            response.raise_for_status()
            return response.text

    def _process_raw_matter(  # type: ignore
        self,
        matter: str,
        volume: VolumeDetail,
        main_toc: list[Tag] | None = None,
        secondary_toc: list[Tag] | None = None,
    ) -> str:
        # Match names of matters in API with the name of templates on github: https://github.com/suttacentral/publications/tree/sujato-templates/templates
        MATTERS_TO_TEMPLATES_NAMES_MAPPING: dict[str, str] = ast.literal_eval(
            os.getenv("MATTERS_TO_TEMPLATES_NAMES_MAPPING")  # type: ignore
        )

        if not MATTERS_TO_TEMPLATES_NAMES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable MATTERS_TO_TEMPLATES_NAMES_MAPPING."
            )
        else:
            try:
                # Get template filename associated with that matter
                _template_name: str = MATTERS_TO_TEMPLATES_NAMES_MAPPING[matter]

                # Fetch Jinja template from file
                template_loader = jinja2.FileSystemLoader(searchpath=EditionParser.HTML_TEMPLATES_DIR)
                template_env = jinja2.Environment(loader=template_loader, autoescape=True)
                template = template_env.get_template(name=_template_name)

                _main_toc_html: str = generate_html_toc(headings=main_toc) if main_toc else ""
                _secondary_toc_html: str | None = generate_html_toc(headings=secondary_toc) if secondary_toc else None

                # variables: dict[str, str | Sequence[str] | bool] = self._match_template_variables_with_config(
                #     volume=volume, main_toc=_main_toc_html, secondary_toc=_secondary_toc_html
                # )
                variables = ""  # TODO

                matter_html = template.render(**variables)  # type: ignore

                return matter_html

            except FileNotFoundError:
                log.warning(f"Matter {matter} is not supported.")

    # TODO: insert parameter front|back-matter and parametrize func accordingly
    def __generate_frontmatter(self) -> None:
        """Fetch a list of frontmatter components and their contents from API, return a dictionary with {<component_name>: <content>} mapping.
        The output is returned for each volume of a publication.
        """
        log.debug("Generating FrontMatters...")

        PREFIX = "/opt/sc/sc-flask/sc-data"
        working_dir: str = self.config.edition.working_dir.removeprefix(PREFIX)

        per_volume_frontmatters: list[dict[str, Any]] = []

        # Parse list of frontmatters for this publication
        for _volume, _main_toc, _secondary_toc in zip(
            self.config.edition.volumes, self._collect_main_toc_headings(), self._collect_secondary_toc()
        ):

            _frontmatter: list[str] = _volume.frontmatter
            matter_types: list[tuple[str, bool]] = [(matter, self._is_html_matter(matter)) for matter in _frontmatter]
            processed_matters: dict[str, Any] = {}
            _main_toc_ = _main_toc if "main-toc" in _frontmatter else None
            _secondary_toc_ = list(_secondary_toc.values()) if "secondary-toc" in _frontmatter else None

            for matter, is_html in matter_types:
                if is_html:
                    processed_matters[matter] = self._process_html_matter(matter=matter, working_dir=working_dir)
                else:
                    processed_matters[matter] = self._process_raw_matter(
                        matter=matter, volume=_volume, main_toc=_main_toc_, secondary_toc=_secondary_toc_
                    )

            per_volume_frontmatters.append(copy(processed_matters))

        self.per_volume_frontmatters = per_volume_frontmatters

    def __generate_covers(self) -> None:
        log.debug("Generating covers...")
        # TODO [58]: implement

    def __generate_backmatter(self) -> None:
        log.debug("Generating BackMatters...")

        PREFIX = "/opt/sc/sc-flask/sc-data"
        working_dir: str = self.config.edition.working_dir.removeprefix(PREFIX)

        per_volume_backmatters: list[dict[str, Any]] = []

        # Parse list of backmatters for this publication
        for _volume in self.config.edition.volumes:

            _backmatter: list[str] = _volume.backmatter
            matter_types: list[tuple[str, bool]] = [(matter, self._is_html_matter(matter)) for matter in _backmatter]
            processed_matters: dict[str, Any] = {}

            for matter, is_html in matter_types:
                if is_html:
                    processed_matters[matter] = self._process_html_matter(matter=matter, working_dir=working_dir)
                else:
                    processed_matters[matter] = self._process_raw_matter(matter=matter, volume=_volume)

            per_volume_backmatters.append(copy(processed_matters))

        self.per_volume_backmatters = per_volume_backmatters

    def collect_all(self) -> EditionResult:
        # Order of execution matters here
        edition = self._create_edition_skeleton()
        operations: list[Callable] = [
            self.set_metadata,
            self.set_filename,
            self.set_mainmatter,
            self.set_main_toc,
            self.set_secondary_toc,
            self.set_frontmatter,
            self.set_backmatter,
        ]
        for _operation in operations:
            EditionParser._on_each_volume(edition=edition, operation=_operation)

        # self.__generate_mainmatter()    # 1.
        # self.__mainmatter_postprocess() # 2.
        # self.__generate_frontmatter()   # 3.
        # self.__generate_backmatter()    # 3.
        # self.__generate_covers()        # 3.
        # txt = "dummy"
        # result = EditionResult()
        # result.write(txt)
        # result.seek(0)
        # return result

    @classmethod
    def get_edition_mapping(cls) -> dict[EditionType, Type[EditionParser]]:
        return {klass.edition_type: klass for klass in cls.__subclasses__()}
