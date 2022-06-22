from __future__ import annotations

import ast
import logging
import os
from abc import ABC
from pathlib import Path
from typing import Any, Callable, Type, cast

import jinja2
import requests
from bs4 import BeautifulSoup, Tag
from jinja2 import Environment, FileSystemLoader, Template

from sutta_publisher.edition_parsers.helper_functions import (
    add_class,
    collect_actual_headings,
    create_html_heading_with_id,
    extract_string,
    fetch_possible_refs,
    find_all_headings,
    find_sutta_title_depth,
    get_heading_depth,
    increment_heading_by_number,
    parse_main_toc_depth,
    process_line,
    remove_all_header,
    remove_all_ul,
)
from sutta_publisher.shared.value_objects.edition import EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import (
    EditionData,
    MainMatter,
    MainMatterPart,
    Node,
    VolumeData,
    VolumePreheadings,
)
from sutta_publisher.shared.value_objects.parser_objects import (
    Blurb,
    Edition,
    MainTableOfContents,
    SecondaryTablesOfContents,
    ToCHeading,
    Volume,
)

log = logging.getLogger(__name__)

ADDITIONAL_HEADINGS = ast.literal_eval(os.getenv("ADDITIONAL_HEADINGS", ""))


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

    # --- operations on whole edition
    def _create_edition_skeleton(self) -> Edition:
        """Creates a collection of empty volumes to work on."""
        # We need to set up volume numbers here to be able to match volume in raw data from API to output volume.
        # We need to be extra careful because:
        # (1) volume_number may be None so raw_data[volume_number] won't work
        # (2) volume_number is 1-based, whereas, raw_data is a list, so it has 0-based index
        # hence the method _get_true_index is used created
        if len(self.raw_data) == 1:  # means only 1 volume
            volumes = [Volume(volume_number=None)]
        else:
            volumes = [Volume(volume_number=num + 1) for num, _ in enumerate(self.raw_data)]

        return Edition(volumes=volumes)

    @staticmethod
    def _get_true_index(volume: Volume) -> int:
        """Get actual volume's index (i.e. where it is in the volumes list in raw_data and collect volume-specific
        edition config)"""
        if volume.volume_number is None:
            return 0  # means there's only 1 volume, so index is 0
        else:
            # volume_number is 1-based index, whereas, lists have 0-based index
            return cast(int, volume.volume_number - 1)

    @staticmethod
    def on_each_volume(edition: Edition, operation: Callable) -> None:
        """Perform an operation on each volume in edition"""
        [operation(volume) for volume in edition.volumes]

    # --- operations on metadata
    def _collect_metadata(self, volume: Volume) -> dict[str, str | int | list[str] | list[Blurb]]:
        _index = EditionParser._get_true_index(volume)
        return {
            "acronym": self.raw_data[_index].acronym,
            "blurbs": self._collect_blurbs(volume),
            "created": self.config.edition.created,
            "creation_process": self.config.publication.creation_process,
            "creator_biography": self.config.publication.creator_bio,
            "creator_name": self.config.publication.creator_name,
            "creator_uid": self.config.publication.creator_uid,
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

    def _collect_blurbs(self, volume: Volume) -> list[Blurb]:
        """Collect blurbs for a given volume.

        Args:
            volume: a volume for which to collect blurbs

        Returns:
            list[str]: blurbs collected as a list of strings
        """
        blurbs: list[Blurb] = []

        _index: int = self._get_true_index(volume)
        _mainmatter: MainMatter = self.raw_data[_index].mainmatter

        for _part in _mainmatter:
            _blurbs_in_mainmatter_part: list[Blurb] = [Blurb.parse_obj(_node) for _node in _part if _node.blurb]
            blurbs.extend(_blurbs_in_mainmatter_part)

        return blurbs

    def set_metadata(self, volume: Volume) -> None:
        """Set attributes with metadata for a volume. If attribute name is unknown
        (no such field in `Volume` definition) skip it."""
        _metadata = self._collect_metadata(volume)

        for _attr, _value in _metadata.items():
            try:
                setattr(volume, _attr, _value)
            except ValueError:
                continue

    def set_filename(self, volume: Volume) -> None:
        """Generate and assigns a proper name for output file to a volume"""
        _translation_title: str = volume.translation_title.replace(" ", "-")
        _date: str = volume.updated if volume.updated else volume.created
        _date = _date[:10]
        _volume_number: str = f"-{volume.volume_number}" if volume.volume_number else ""
        _file_extension: str = self.edition_type.name

        volume.filename = f"{_translation_title}-{volume.creator_uid}-{_date}{_volume_number}.{_file_extension}"

    # --- operations on mainmatter
    def _generate_mainmatter(self, volume: Volume) -> str:

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

        # Postprocess mainmatter
        _index: int = EditionParser._get_true_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _mainmatter_raw: str = self._process_mainmatter(_raw_data.mainmatter)

        _mainmatter_html: BeautifulSoup = BeautifulSoup(_mainmatter_raw, "lxml")

        mainmatter: str = self._postprocess_mainmatter(mainmatter=_mainmatter_html, volume=volume)

        return mainmatter

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
        single_lines: list[str] = []

        # Some nodes are branches not leaves - they contain preheadings/headings but no mainmatter, we skip them.
        if not node.mainmatter.markup:
            return ""

        else:
            # Only store segment_id if it has matching markup (prune empty strings)
            _segment_ids: list[str] = [
                _id for _id, _markup in node.mainmatter.markup.items() if _markup
            ]  # type: ignore

            for _id in _segment_ids:
                try:
                    single_lines.append(
                        process_line(
                            markup=node.mainmatter.markup[_id],
                            segment_id=_id,
                            text=node.mainmatter.main_text.get(_id, ""),
                            note=node.mainmatter.notes.get(_id, "") if node.mainmatter.notes else "",
                            references=node.mainmatter.reference.get(_id, "") if node.mainmatter.reference else "",
                            possible_refs=self.possible_refs,
                        )
                    )
                except AttributeError:
                    raise SystemExit(f"Error while processing segment {_id}. Stopping.")
            return "".join(single_lines)  # putting content of one node together

    @staticmethod
    def _insert_span_tags(headings: list[Tag], nodes: list[Node]) -> None:
        """Inserts <span class='sutta-heading {acronym | translation-title | root-title}'> tags into
        sutta-title headings"""
        span_tags_to_add = {"acronym": "acronym", "name": "translated-title", "root_name": "root-title"}
        for heading, node in zip(headings, nodes):
            title = heading.get_text()
            heading.string = ""
            for attr, css_class in span_tags_to_add.items():
                if attr == "name":
                    span = BeautifulSoup(parser="lxml").new_tag("span", attrs={"class": f"sutta-heading {css_class}"})
                    span.string = title
                    heading.append(span)
                elif node_attr := getattr(node, attr, None):
                    span = BeautifulSoup(parser="lxml").new_tag("span", attrs={"class": f"sutta-heading {css_class}"})
                    span.string = node_attr
                    heading.append(span)

    def _add_indices_to_note_refs(self, mainmatter: BeautifulSoup) -> None:
        """Add indices to note-ref anchor tags"""
        last_id = self.config.edition.noteref_id
        _noteref_anchors = mainmatter.find_all("a", id="noteref-{number}")
        for tag in _noteref_anchors:
            last_id += 1
            tag["href"] = tag["href"].format(number=last_id)
            tag["id"] = tag["id"].format(number=last_id)
            tag.string = tag.string.format(number=last_id)
        self.config.edition.noteref_id = last_id

    def _postprocess_mainmatter(self, mainmatter: BeautifulSoup, volume: Volume) -> str:
        """Apply some additional postprocessing and insert additional headings to a crude mainmatter"""

        _index: int = self._get_true_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _sutta_title_depth: int = max(_raw_data.depths.values())

        _header_tags = mainmatter.find_all("header")
        # Remove all <ul>...</ul> tags from <header>...</header> elements
        remove_all_ul(headers=_header_tags)
        # Remove all <header>...</header> tags from mainmatter, but keep their contents
        remove_all_header(headers=_header_tags)

        # Change numbers of all headings according to how many additional preheadings are. If there are 2 preheadings,
        # h1 headings become h3 headings.
        _additional_depth: int = _sutta_title_depth - 1
        for heading in find_all_headings(mainmatter):
            increment_heading_by_number(by_number=_additional_depth, heading=heading)

        # Insert preheadings
        EditionParser._insert_preheadings(
            mainmatter=mainmatter,
            preheadings=_raw_data.preheadings,
            tree=_raw_data.depths,
        )

        # Add class "heading" for all HTML headings between h1 and hX which has class "sutta-title"
        _headings = collect_actual_headings(end_depth=_sutta_title_depth, html=mainmatter)
        add_class(tags=_headings, class_="heading")

        # Add class "section-title" for all headings that are not sutta-titles
        add_class(tags=[h for h in _headings if "sutta-title" not in h.attrs["class"]], class_="section-title")

        # Add <span> tags with acronyms, translated and root titles into sutta-title headings
        _sutta_headings: list[Tag] = [h for h in _headings if h.name == f"h{_sutta_title_depth}"]
        _sutta_nodes: list[Node] = [_node for _part in _raw_data.mainmatter for _node in _part if _node.type == "leaf"]
        self._insert_span_tags(headings=_sutta_headings, nodes=_sutta_nodes)

        # Add class "subheading" for all HTML headings below hX with class "sutta-title"
        _start_depth = _sutta_title_depth + 1
        _subheadings = collect_actual_headings(start_depth=_start_depth, end_depth=999, html=mainmatter)
        add_class(tags=_subheadings, class_="subheading")

        # Add the numbering to note reference anchors
        self._add_indices_to_note_refs(mainmatter=mainmatter)

        return cast(str, extract_string(mainmatter))

    @staticmethod
    def _insert_preheadings(
        mainmatter: BeautifulSoup,
        preheadings: VolumePreheadings,
        tree: dict,
    ) -> None:
        """Insert preheadings (additional HTML tags) into mainmatter"""
        tree_keys = list(tree.keys())

        for mainmatter_preheadings in preheadings:
            for preheading_group in mainmatter_preheadings:

                # Firstly we need the first sutta-title tag in given section (preheading group)
                target: Tag = mainmatter.find(id=tree_keys[tree_keys.index(preheading_group[-1].uid) + 1])

                for _preheading in preheading_group:
                    # Then we insert all section headings (preheadings) before that sutta-title tag.
                    # The exemplary structure looks like this:
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

                    target.insert_before(
                        create_html_heading_with_id(
                            html=mainmatter, depth=tree[_preheading.uid], text=_preheading.name, id_=_preheading.uid
                        )
                    )

    def set_mainmatter(self, volume: Volume) -> None:
        """Add a mainmatter to a volume"""
        _mainmatter = self._generate_mainmatter(volume)

        volume.mainmatter = _mainmatter

    # --- operations on tables of contents
    def _collect_main_toc(self, html: BeautifulSoup) -> list[Tag]:
        """Collect all headings, which belong to main ToCs.

        The collection is divided by volume.

        Returns:
            list[Tag]: Headings to be placed in main ToCs, delivered as a list of HTML tags
        """
        log.debug("Collecting headings for the main ToCs...")

        _depth: int = parse_main_toc_depth(depth=self.config.edition.main_toc_depth, html=html)
        headings: list[Tag] = collect_actual_headings(end_depth=_depth, html=html)

        return headings

    def _collect_main_toc_uids(self, tags: list[Tag]) -> list[str]:
        """Return a list of unique IDs of main toc headings"""
        return [tag["id"] if tag.get("id", None) else tag.parent["id"] for tag in tags]

    def _create_extra_heading(self, heading: str, display_name: str) -> Tag:
        """Create an extra Tag: <h1 id='{item}'>{item}</h1>"""
        soup = BeautifulSoup(parser="lxml")
        tag = soup.new_tag("h1", id=heading)
        tag.string = display_name
        return tag

    def _insert_extra_headings(self, _headings: list[ToCHeading], volume: Volume) -> None:
        """Insert extra frontmatter heading at the beginning
        and backmatter headings at the end of the collected_headings list"""
        _index: int = EditionParser._get_true_index(volume)
        frontmatter_headings: list[ToCHeading] = [
            ToCHeading.parse_obj(
                {
                    "acronym": None,
                    "depth": 1,
                    "name": display_name,
                    "tag": self._create_extra_heading(heading=heading, display_name=display_name),
                    "type": "front",
                    "uid": heading,
                }
            )
            for heading, display_name in ADDITIONAL_HEADINGS["frontmatter"]
            if any(heading in matter for matter in self.config.edition.volumes[_index].frontmatter)
        ]
        _headings[0:0] = frontmatter_headings

        backmatter_headings: list[ToCHeading] = [
            ToCHeading.parse_obj(
                {
                    "acronym": None,
                    "depth": 1,
                    "name": display_name,
                    "tag": self._create_extra_heading(heading=heading, display_name=display_name),
                    "type": "back",
                    "uid": heading.replace("notes", "endnotes"),  # TODO: matter names should be unified
                }
            )
            for heading, display_name in ADDITIONAL_HEADINGS["backmatter"]
            if any(heading in matter for matter in self.config.edition.volumes[_index].backmatter)
        ]
        _headings.extend(backmatter_headings)

    def set_main_toc(self, volume: Volume) -> None:
        """Add main table of contents to a volume"""
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        _heading_tags = self._collect_main_toc(html=_mainmatter)
        _heading_uids = self._collect_main_toc_uids(tags=_heading_tags)
        _index = EditionParser._get_true_index(volume)
        _data: list[Node] = [
            _node for _part in self.raw_data[_index].mainmatter for _node in _part if _node.uid in _heading_uids
        ]
        _tree = self.raw_data[_index].depths

        _headings: list[ToCHeading] = [
            ToCHeading.parse_obj(
                {
                    "acronym": node.acronym,
                    "depth": _tree[node.uid],
                    "name": node.name,
                    "root_name": node.root_name,
                    "tag": tag,
                    "type": node.type,
                    "uid": node.uid,
                }
            )
            for tag, node in zip(_heading_tags, _data)
        ]
        self._insert_extra_headings(_headings=_headings, volume=volume)
        volume.main_toc = MainTableOfContents.parse_obj({"headings": _headings})

    @staticmethod
    def _collect_secondary_toc(
        html: BeautifulSoup, main_toc_depth: int, secondary_toc_depth: int
    ) -> dict[Tag, list[Tag]]:
        """Generate a mapping of the deepest main ToC headings
        and a list of their children secondary ToC headings"""
        log.debug("Collecting headings for secondary ToCs...")

        _secondary_tocs_headings: list[Tag] = collect_actual_headings(
            start_depth=main_toc_depth, end_depth=secondary_toc_depth, html=html
        )

        secondary_toc_mapping: dict[Tag, list[Tag]] = {}

        _parent = None
        for _heading in _secondary_tocs_headings:
            if get_heading_depth(_heading) == main_toc_depth:
                _parent = _heading
                secondary_toc_mapping[_parent] = []
            else:
                secondary_toc_mapping[_parent].append(_heading)

        return secondary_toc_mapping

    def _collect_sec_toc_uids(self, headings: dict[Tag, list[Tag]]) -> list[str]:
        """Return a list of unique IDs of secondary toc headings"""
        return [h["id"] if h.get("id", None) else h.parent["id"] for hs in headings.values() for h in hs]

    def set_secondary_toc(self, volume: Volume) -> None:
        """Add secondary tables of contents to a volume"""
        if secondary_toc := self.config.edition.secondary_toc:
            _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
            _main_toc_depth: int = parse_main_toc_depth(depth=self.config.edition.main_toc_depth, html=_mainmatter)
            _secondary_toc_depth: int = find_sutta_title_depth(html=_mainmatter)

            _headings: dict[Tag, list[Tag]] = EditionParser._collect_secondary_toc(
                html=_mainmatter, main_toc_depth=_main_toc_depth, secondary_toc_depth=_secondary_toc_depth
            )
            _heading_uids: list[str] = self._collect_sec_toc_uids(headings=_headings)
            _index: int = EditionParser._get_true_index(volume)
            _data: list[Node] = [
                _node for _part in self.raw_data[_index].mainmatter for _node in _part if _node.uid in _heading_uids
            ]
            _tree = self.raw_data[_index].depths

            _soc_headings: dict[Tag, list[ToCHeading]] = {}
            for heading, subheadings in _headings.items():
                _soc_headings[heading] = []
                for tag in subheadings:
                    node = _data.pop(0)
                    _soc_headings[heading].append(
                        ToCHeading.parse_obj(
                            {
                                "acronym": node.acronym,
                                "depth": _tree[node.uid],
                                "name": node.name,
                                "root_name": node.root_name,
                                "tag": tag,
                                "type": node.type,
                                "uid": node.uid,
                            }
                        )
                    )

            volume.secondary_toc = SecondaryTablesOfContents.parse_obj({"headings": _soc_headings})
        else:
            log.debug(f"Edition without secondary ToCs. {secondary_toc=}")

    # --- operations on frontmatter and backmatter
    def _collect_matters(self, matters: list[str], volume: Volume) -> list[str]:
        _types_matters: list[tuple[bool, str]] = [
            (EditionParser._is_html_matter(_matter), _matter) for _matter in matters
        ]

        PREFIX = "/opt/sc/sc-flask/sc-data"
        _working_dir: str = self.config.edition.working_dir.removeprefix(PREFIX)

        matters_collected: list[str] = []

        for _is_html, _matter in _types_matters:
            if _is_html:
                _html_str: str = EditionParser._process_html_matter(matter=_matter, working_dir=_working_dir)

                # add id attribute to enable front and backmatter links in table of contents
                if item := [
                    matter
                    for matter, _ in ADDITIONAL_HEADINGS["frontmatter"] + ADDITIONAL_HEADINGS["backmatter"]
                    if matter in _matter
                ]:
                    _html_str = _html_str.replace("<article", f"<article id='{item[0]}'")

            elif _matter == "main-toc":
                _html_str = EditionParser._process_main_toc_as_matter(matter=volume.main_toc)
            else:
                _html_str = EditionParser._process_raw_matter(matter=_matter, volume=volume)
            matters_collected.append(_html_str)

        return matters_collected

    @staticmethod
    def _is_html_matter(matter: str) -> bool:
        """Determines whether a matter is an HTML file or a raw text

        Args:
            matter: a path to file with a matter returned by an API response

        Returns:
            bool: True if a matter is an HTML file, otherwise False
        """
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

    @staticmethod
    def _process_raw_matter(matter: str, volume: Volume) -> str:
        # Match names of matters in API with the name of templates
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
                _template_loader: FileSystemLoader = jinja2.FileSystemLoader(
                    searchpath=EditionParser.HTML_TEMPLATES_DIR
                )
                _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)
                _template: Template = _template_env.get_template(name=_template_name)

                # Throw all all attributes at the templates, only relevant variables will stick as long as
                # their names match variable names in jinja2 template.
                matter_html: str = _template.render(**volume.dict())

                return matter_html

            except FileNotFoundError:
                log.warning(f"Matter '{matter}' is not supported.")
                return ""

    @staticmethod
    def _process_main_toc_as_matter(matter: MainTableOfContents) -> str:
        MATTERS_TO_TEMPLATES_NAMES_MAPPING: dict[str, str] = ast.literal_eval(
            os.getenv("MATTERS_TO_TEMPLATES_NAMES_MAPPING")  # type: ignore
        )

        if not MATTERS_TO_TEMPLATES_NAMES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable MATTERS_TO_TEMPLATES_NAMES_MAPPING."
            )
        else:
            try:
                _template_name: str = MATTERS_TO_TEMPLATES_NAMES_MAPPING["main-toc"]
                _template_loader: FileSystemLoader = jinja2.FileSystemLoader(
                    searchpath=EditionParser.HTML_TEMPLATES_DIR
                )
                _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)
                _template: Template = _template_env.get_template(name=_template_name)
                _matter: str = matter.to_html_str(_template)

                return _matter

            except FileNotFoundError:
                log.warning(f"Matter '{matter}' is not supported.")
                return ""

    def set_frontmatter(self, volume: Volume) -> None:
        """Add a frontmatter to a volume"""
        _index: int = EditionParser._get_true_index(volume)
        _matters: list[str] = self.config.edition.volumes[_index].frontmatter
        volume.frontmatter = self._collect_matters(volume=volume, matters=_matters)

    def set_notes(self, volume: Volume) -> None:
        """Add notes to a volume"""
        _index: int = EditionParser._get_true_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _raw_node_mainmatters = [node.mainmatter for part in _raw_data.mainmatter for node in part]
        _raw_notes: list[str] = [
            note for mainmatter in _raw_node_mainmatters if mainmatter.notes for note in mainmatter.notes.values()
        ]
        volume.notes = _raw_notes

    def set_backmatter(self, volume: Volume) -> None:
        """Add a backmatter to a volume"""
        _index: int = EditionParser._get_true_index(volume)
        _matters: list[str] = self.config.edition.volumes[_index].backmatter
        volume.backmatter = self._collect_matters(volume=volume, matters=_matters)

    @staticmethod
    def _process_secondary_toc(matter: SecondaryTablesOfContents) -> dict[Tag, str]:
        MATTERS_TO_TEMPLATES_NAMES_MAPPING: dict[str, str] = ast.literal_eval(
            os.getenv("MATTERS_TO_TEMPLATES_NAMES_MAPPING")  # type: ignore
        )

        if not MATTERS_TO_TEMPLATES_NAMES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable MATTERS_TO_TEMPLATES_NAMES_MAPPING."
            )
        else:
            try:
                _template_name: str = MATTERS_TO_TEMPLATES_NAMES_MAPPING["secondary-toc"]
                _template_loader: FileSystemLoader = jinja2.FileSystemLoader(
                    searchpath=EditionParser.HTML_TEMPLATES_DIR
                )
                _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)
                _template: Template = _template_env.get_template(name=_template_name)
                _secondary_tocs: dict[Tag, str] = matter.to_html_str(_template)

                return _secondary_tocs

            except FileNotFoundError:
                raise SystemExit(f"Matter '{matter}' is not supported.")

    def add_secondary_toc_to_mainmatter(self, volume: Volume) -> None:
        """Add secondary toc to mainmatter"""
        if secondary_toc := self.config.edition.secondary_toc:
            _secondary_tocs = self._process_secondary_toc(volume.secondary_toc)
            _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
            _main_toc_depth: int = parse_main_toc_depth(depth=self.config.edition.main_toc_depth, html=_mainmatter)
            for heading, toc in zip(_mainmatter.find_all(f"h{_main_toc_depth}"), _secondary_tocs.values()):
                heading.insert_after(BeautifulSoup(toc, "html.parser"))

            volume.mainmatter = extract_string(_mainmatter)
        else:
            log.debug(f"Edition without secondary ToCs. {secondary_toc=}")

    def _generate_cover(self, volume: Volume) -> Any:
        log.debug("Generating covers...")
        # TODO [58]: implement

    def set_cover(self, volume: Volume) -> None:
        volume.cover = self._generate_cover(volume)

    # --- putting it all together
    def collect_all(self) -> Edition:
        """Call all component methods responsible for generating each part of base HTML"""
        # Order of execution matters here
        edition: Edition = self._create_edition_skeleton()
        _operations: list[Callable] = [
            self.set_metadata,
            self.set_filename,
            self.set_mainmatter,
            self.set_main_toc,
            self.set_secondary_toc,
            self.set_frontmatter,
            self.set_notes,
            self.set_backmatter,
            self.add_secondary_toc_to_mainmatter,
        ]
        for _operation in _operations:
            EditionParser.on_each_volume(edition=edition, operation=_operation)

        return edition

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
        """Match edition types with their respective parsers"""
        return {klass.edition_type: klass for klass in cls.__subclasses__()}
