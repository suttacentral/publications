from __future__ import annotations

import ast
import logging
import os
import tempfile
from abc import ABC
from pathlib import Path
from typing import Callable, cast

import jinja2
import requests
from bs4 import BeautifulSoup, Tag
from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from sutta_publisher.edition_parsers.helper_functions import (
    add_class,
    collect_actual_headings,
    extract_string,
    fetch_possible_refs,
    find_all_headings,
    find_sutta_title_depth,
    get_heading_depth,
    get_true_volume_index,
    increment_heading_by_number,
    make_absolute_links,
    parse_main_toc_depth,
    process_line,
    remove_all_header,
    remove_all_ul,
    remove_empty_tags,
    validate_node,
)
from sutta_publisher.shared.value_objects.edition import EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, MainMatterPart, Node, VolumeData
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
ADDITIONAL_PANNASAKA_IDS = ast.literal_eval(os.getenv("ADDITIONAL_PANNASAKA_IDS", ""))
MATTERS_TO_TEMPLATES_MAPPING: dict[str, str] = ast.literal_eval(os.getenv("MATTERS_TO_TEMPLATES_MAPPING", ""))
SUTTACENTRAL_URL = os.getenv("SUTTACENTRAL_URL", "/")


class EditionParser(ABC):
    HTML_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "html"
    IMAGES_DIR = Path(__file__).parent.parent / "images"
    TEMP_DIR = Path(tempfile.gettempdir())
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
    def on_each_volume(edition: Edition, operation: Callable) -> None:
        """Perform an operation on each volume in edition"""
        [operation(volume) for volume in edition.volumes]

    # --- operations on metadata
    def _collect_metadata(self, volume: Volume) -> dict[str, str | int | list[str] | list[Blurb]]:
        _index = get_true_volume_index(volume)
        return {
            "blurbs": self._collect_blurbs(volume),
            "cover_bleed": self.config.edition.cover_bleed,
            "cover_theme_color": self.config.edition.cover_theme_color,
            "created": self.config.edition.created,
            "creation_process": self.config.publication.creation_process,
            "creator_biography": self.config.publication.creator_bio,
            "creator_name": self.config.publication.creator_name,
            "creator_uid": self.config.publication.creator_uid,
            "edition_number": self.config.edition.edition_number,
            "first_published": self.config.publication.first_published,
            "number_of_volumes": self.config.edition.number_of_volumes,
            "page_height": self.config.edition.page_height,
            "page_width": self.config.edition.page_width,
            "publication_blurb": self.config.edition.publication_blurb,
            "publication_isbn": self.config.edition.publication_isbn,
            "publication_number": self.config.edition.publication_number,
            "publication_url": self._get_publication_url(),
            "publication_type": self.config.edition.publication_type.name,
            "root_name": self.config.publication.root_lang_name,
            "root_title": self.config.publication.root_title,
            "source_url": self.config.publication.source_url,
            "text_description": self.config.publication.text_description,
            "text_uid": self.config.edition.text_uid,
            "translation_lang_iso": self.config.publication.translation_lang_iso,
            "translation_lang_name": self.config.publication.translation_lang_name,
            "translation_subtitle": self.config.publication.translation_subtitle,
            "translation_title": self.config.publication.translation_title,
            "updated": self.config.edition.updated,
            "volume_acronym": self.config.edition.volumes[_index].volume_acronym,
            "volume_blurb": self.config.edition.volumes[_index].volume_blurb,
            "volume_isbn": self.config.edition.volumes[_index].volume_isbn,
            "volume_root_title": self.config.edition.volumes[_index].volume_root_title,
            "volume_translation_title": self.config.edition.volumes[_index].volume_translation_title,
        }

    def _collect_blurbs(self, volume: Volume) -> list[Blurb]:
        """Collect blurbs for a given volume.

        Args:
            volume: a volume for which to collect blurbs

        Returns:
            list[str]: blurbs collected as a list of strings
        """
        blurbs: list[Blurb] = []

        _index: int = get_true_volume_index(volume)
        _mainmatter: MainMatter = self.raw_data[_index].mainmatter

        for _part in _mainmatter:
            _blurbs_in_mainmatter_part: list[Blurb] = [Blurb.parse_obj(_node) for _node in _part if _node.blurb]
            blurbs.extend(_blurbs_in_mainmatter_part)

        return blurbs

    def _get_publication_url(self) -> str:
        """Returns publication url: {suttacentral_url}/editions/{UID}/{ISO}/{author}"""
        return f"{SUTTACENTRAL_URL}editions/{self.config.edition.text_uid}/{self.config.publication.translation_lang_iso}/{self.config.publication.creator_uid}"

    def append_file_paths(self, volume: Volume, paths: list) -> None:
        """Appends paths of generated files to a given volume"""
        for path in paths:
            volume.file_paths.append(path)

    def set_metadata(self, volume: Volume) -> None:
        """Set attributes with metadata for a volume. If attribute name is unknown
        (no such field in `Volume` definition) skip it."""
        _metadata = self._collect_metadata(volume)

        for _attr, _value in _metadata.items():
            try:
                setattr(volume, _attr, _value)
            except ValueError:
                continue

    def set_filenames(self, volume: Volume) -> None:
        """Generate and assign a proper name for output files to a volume"""
        _translation_title: str = volume.translation_title.replace(" ", "-")
        _date: str = volume.updated if volume.updated else volume.created
        _date = _date[:10]
        _volume_number: str = f"-{volume.volume_number}" if volume.volume_number else ""

        volume.filename = f"{_translation_title}-{volume.creator_uid}-{_date}{_volume_number}"
        volume.cover_filename = f"{volume.filename}-cover"

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
        _volume_index: int = get_true_volume_index(volume)

        _raw_data: VolumeData = self.raw_data[_volume_index]
        _mainmatter_raw: str = self._process_mainmatter(mainmatter=_raw_data.mainmatter, volume_index=_volume_index)

        _mainmatter_html: BeautifulSoup = BeautifulSoup(_mainmatter_raw, "lxml")

        mainmatter: str = self._postprocess_mainmatter(mainmatter=_mainmatter_html, volume=volume)

        return mainmatter

    def _process_mainmatter(self, mainmatter: MainMatter, volume_index: int) -> str:
        """Mainmatter may consist of several parts, deal with them separately and concatenate results into string."""
        return "".join([self._process_mainmatter_part(part=_part, volume_index=volume_index) for _part in mainmatter])

    def _process_mainmatter_part(self, part: MainMatterPart, volume_index: int) -> str:
        """Part of mainmatter consists of nodes, deal with them separately and concatenate results into a string."""
        return "".join([self._process_mainmatter_node(node=_node, volume_index=volume_index) for _node in part])

    def _process_mainmatter_node(self, node: Node, volume_index: int) -> str:
        """Parse a single 'node' from API and return a ready HTML string.

        Each node's content is split between dictionaries with lines of text, markup and references.
        Keys are always segment IDs.
        """

        validate_node(node)

        # *** Branches (section headings) with no content ***
        if node.type == "branch":

            # Skip the 1st branch in editions that consist of only 1 mainmatter and 1 volume
            if (
                node.uid != self.config.edition.text_uid
                or len(self.config.edition.volumes[volume_index].mainmatter) > 1
                or self.config.edition.number_of_volumes > 1
            ):
                try:
                    _heading_depth = self.raw_data[volume_index].depths[node.uid]
                except KeyError:
                    raise SystemExit(
                        f"Error while inserting section heading '{node.uid}'. Heading ID not found in structure tree. Stopping."
                    )
                return f"<h{_heading_depth} class='section-title' id='{node.uid}'>{node.name}</h{_heading_depth}>"

            else:
                return ""

        # *** Leaves (suttas or ranges of suttas) ***

        # Skip empty leaves with no content
        elif not node.mainmatter.markup:
            return ""

        # Leaves with content
        else:
            # Only store segment_id if it has matching markup (prune empty strings)
            _segment_ids: list[str] = [
                _id for _id, _markup in node.mainmatter.markup.items() if _markup
            ]  # type: ignore

            single_lines: list[str] = []

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
                    raise SystemExit(f"Error while processing segment '{_id}'. Stopping.")
            return "".join(single_lines)  # putting content of one node together

    @staticmethod
    def _insert_span_tags(headings: list[Tag], nodes: list[Node]) -> None:
        """Inserts <span class='sutta-heading {acronym | translation-title | root-title}'> tags into
        sutta-title headings"""
        SPAN_TAGS_TO_ADD = {"acronym": "acronym", "name": "translated-title", "root_name": "root-title"}
        for heading, node in zip(headings, nodes):
            title = heading.get_text()
            heading.string = ""
            for attr, css_class in SPAN_TAGS_TO_ADD.items():
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

    def _unwrap_verses(self, mainmatter: BeautifulSoup) -> None:
        """Unwrap all <span class='verse-line'> tags and insert <br> at the end of each verse except the last one
        in given paragraph"""
        for _paragraph in mainmatter.find_all("p"):
            for _i, _span in enumerate(_spans := _paragraph.find_all("span", class_="verse-line")):
                if _i + 1 < len(_spans):
                    _span.insert_after(mainmatter.new_tag("br"))
                _span.unwrap()

    def _postprocess_mainmatter(self, mainmatter: BeautifulSoup, volume: Volume) -> str:
        """Apply some additional postprocessing and insert additional headings to a crude mainmatter"""

        _index: int = get_true_volume_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _sutta_title_depth: int = max(_raw_data.depths.values())

        _header_tags = mainmatter.find_all("header")
        # Remove all <ul>...</ul> tags from <header>...</header> elements
        remove_all_ul(headers=_header_tags)
        # Remove all <header>...</header> tags from mainmatter, but keep their contents
        remove_all_header(headers=_header_tags)

        # Change depth of all headings but section-titles
        _additional_depth: int = _sutta_title_depth - 1
        for heading in find_all_headings(mainmatter):
            increment_heading_by_number(by_number=_additional_depth, heading=heading)

        # Remove all empty tags
        remove_empty_tags(html=mainmatter)

        # Add class "heading" for all HTML headings between h1 and hX which has class "sutta-title"
        _headings = collect_actual_headings(end_depth=_sutta_title_depth, html=mainmatter)
        add_class(tags=_headings, class_="heading")

        # Add <span> tags with acronyms, translated and root titles into sutta-title headings
        _sutta_headings: list[Tag] = [h for h in _headings if h.name == f"h{_sutta_title_depth}"]
        _sutta_nodes: list[Node] = [
            _node
            for _part in _raw_data.mainmatter
            for _node in _part
            if _node.type == "leaf" and _node.mainmatter.markup
        ]
        EditionParser._insert_span_tags(headings=_sutta_headings, nodes=_sutta_nodes)

        # Add class "subheading" for all HTML headings below hX with class "sutta-title"
        _start_depth = _sutta_title_depth + 1
        _subheadings = collect_actual_headings(start_depth=_start_depth, end_depth=999, html=mainmatter)
        add_class(tags=_subheadings, class_="subheading")

        # Add the numbering to note reference anchors
        self._add_indices_to_note_refs(mainmatter=mainmatter)

        # Remove <span class="verse-line"> tags and insert <br> tags
        self._unwrap_verses(mainmatter=mainmatter)

        # Insert <br> after <span class="speaker">
        for _span in mainmatter.find_all("span", class_="speaker"):
            _span.insert_after(mainmatter.new_tag("br"))

        # Find pannasa headings and add class "pannasaka-heading"
        _pannasa = mainmatter.find_all(id=lambda x: x and (x.endswith("pannasaka") or x in ADDITIONAL_PANNASAKA_IDS))
        add_class(tags=_pannasa, class_="pannasaka-heading")

        return cast(str, extract_string(mainmatter))

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

    def _create_additional_heading(self, heading: str, display_name: str) -> Tag:
        """Create an additional Tag: <h1 id='{item}'>{item}</h1>"""
        soup = BeautifulSoup(parser="lxml")
        tag = soup.new_tag("h1", id=heading)
        tag.string = display_name
        return tag

    def _insert_additional_headings(self, _headings: list[ToCHeading], volume: Volume) -> None:
        """Insert additional frontmatter headings at the beginning
        and backmatter headings at the end of the collected_headings list"""
        _index: int = get_true_volume_index(volume)
        frontmatter_headings: list[ToCHeading] = [
            ToCHeading.parse_obj(
                {
                    "acronym": None,
                    "depth": 1,
                    "name": display_name,
                    "tag": self._create_additional_heading(heading=heading, display_name=display_name),
                    "type": "frontmatter",
                    "uid": heading,
                }
            )
            for heading, display_name in ADDITIONAL_HEADINGS["frontmatter"]
            if any(heading in matter for matter in self.config.edition.volumes[_index].frontmatter)
        ]
        _headings[0:0] = frontmatter_headings
        self.raw_data[_index].tree[0:0] = [_heading.uid for _heading in frontmatter_headings]

        backmatter_headings: list[ToCHeading] = [
            ToCHeading.parse_obj(
                {
                    "acronym": None,
                    "depth": 1,
                    "name": display_name,
                    "tag": self._create_additional_heading(heading=heading, display_name=display_name),
                    "type": "backmatter",
                    "uid": heading,
                }
            )
            for heading, display_name in ADDITIONAL_HEADINGS["backmatter"]
            if any(heading in matter for matter in self.config.edition.volumes[_index].backmatter)
        ]
        _headings.extend(backmatter_headings)
        self.raw_data[_index].tree.extend([_heading.uid for _heading in backmatter_headings])

    @staticmethod
    def _insert_samyutta_numbers(headings: list[ToCHeading]) -> None:
        """Insert hardcoded uid at the beginning of every samyutta heading in place

        Before:
            Linked Discourses With Deities
        After:
            SN 1: Linked Discourses With Deities"""
        for _heading in headings:
            if _heading.depth == 2:
                _new_name = f"{_heading.uid[:2].upper()} {_heading.uid[2:]}: {_heading.name}"
                _heading.name = _new_name
                _heading.tag.string = _new_name

    def set_main_toc(self, volume: Volume) -> None:
        """Add main table of contents to a volume"""
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        _heading_tags = self._collect_main_toc(html=_mainmatter)
        _heading_uids = self._collect_main_toc_uids(tags=_heading_tags)
        _index = get_true_volume_index(volume)
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
        self._insert_additional_headings(_headings=_headings, volume=volume)

        # Applies to SN edition only
        if volume.text_uid == "sn":
            EditionParser._insert_samyutta_numbers(headings=_headings)

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
            _index: int = get_true_volume_index(volume)
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
                    if _matter.endswith(f"/{matter}.html")
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
    def _get_template(name: str) -> Template:
        # Match names of matters in API with the name of templates
        if not MATTERS_TO_TEMPLATES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable MATTERS_TO_TEMPLATES_MAPPING."
            )
        else:
            try:
                _template_name: str = MATTERS_TO_TEMPLATES_MAPPING[name]
            except KeyError:
                raise EnvironmentError(
                    f"'MATTERS_TO_TEMPLATES_MAPPING' in .env_public file lacks required key-value pair for {name} template."
                )

            _template_loader: FileSystemLoader = jinja2.FileSystemLoader(searchpath=EditionParser.HTML_TEMPLATES_DIR)
            _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)

            try:
                template: Template = _template_env.get_template(name=_template_name)
            except TemplateNotFound:
                raise TemplateNotFound(f"Template '{_template_name}' not found.")

            return template

    @staticmethod
    def _process_raw_matter(matter: str, volume: Volume) -> str:
        _template: Template = EditionParser._get_template(name=matter)
        return _template.render(**volume.dict(exclude_none=True, exclude_unset=True))

    @staticmethod
    def _process_main_toc_as_matter(matter: MainTableOfContents) -> str:
        _template: Template = EditionParser._get_template(name="main-toc")
        return matter.to_html_str(_template)  # type: ignore

    def set_frontmatter(self, volume: Volume) -> None:
        """Add a frontmatter to a volume"""
        _index: int = get_true_volume_index(volume)
        _matters: list[str] = self.config.edition.volumes[_index].frontmatter
        volume.frontmatter = self._collect_matters(volume=volume, matters=_matters)

    def set_endnotes(self, volume: Volume) -> None:
        """Add endnotes to a volume"""
        _index: int = get_true_volume_index(volume)
        _raw_data: VolumeData = self.raw_data[_index]
        _raw_nodes = [node.mainmatter for part in _raw_data.mainmatter for node in part]
        _raw_endnotes: list[str] = [note for node in _raw_nodes if node.notes for note in node.notes.values() if note]
        volume.endnotes = _raw_endnotes

    def set_backmatter(self, volume: Volume) -> None:
        """Add a backmatter to a volume"""
        _index: int = get_true_volume_index(volume)
        _matters: list[str] = self.config.edition.volumes[_index].backmatter
        volume.backmatter = self._collect_matters(volume=volume, matters=_matters)

    @staticmethod
    def _process_secondary_toc(matter: SecondaryTablesOfContents) -> dict[Tag, str]:
        _template: Template = EditionParser._get_template(name="secondary-toc")
        return matter.to_html_str(_template)  # type: ignore

    def add_secondary_toc_to_mainmatter(self, volume: Volume) -> None:
        """Add secondary toc to mainmatter"""
        if secondary_toc := self.config.edition.secondary_toc:
            _secondary_tocs = EditionParser._process_secondary_toc(volume.secondary_toc)
            _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
            _main_toc_depth: int = parse_main_toc_depth(depth=self.config.edition.main_toc_depth, html=_mainmatter)
            for heading, toc in zip(_mainmatter.find_all(f"h{_main_toc_depth}"), _secondary_tocs.values()):
                heading.insert_after(BeautifulSoup(toc, "html.parser"))

            volume.mainmatter = extract_string(_mainmatter)
        else:
            log.debug(f"Edition without secondary ToCs. {secondary_toc=}")

    def process_front_and_backmatter_links(self, volume: Volume) -> None:
        """Make all frontmatter and backmatter relative links absolute.
        Relative links are used by Suttacentral website, but they do not work in our output files."""
        _volume_matters = ["frontmatter", "backmatter"]
        for _matters in _volume_matters:
            _processed_matters = []
            for _matter in getattr(volume, _matters):
                _processed_matters.append(make_absolute_links(_matter))
            setattr(volume, _matters, _processed_matters)

    # --- putting it all together
    def collect_all(self) -> Edition:
        """Call all component methods responsible for generating each part of base HTML"""
        # Order of execution matters here
        edition: Edition = self._create_edition_skeleton()
        _operations: list[Callable] = [
            self.set_metadata,
            self.set_filenames,
            self.set_mainmatter,
            self.set_main_toc,
            self.set_secondary_toc,
            self.set_frontmatter,
            self.set_endnotes,
            self.set_backmatter,
            # operations to execute when all matters are set
            self.add_secondary_toc_to_mainmatter,
            self.process_front_and_backmatter_links,
        ]
        for _operation in _operations:
            EditionParser.on_each_volume(edition=edition, operation=_operation)

        return edition

    @classmethod
    def get_edition_mapping(cls, mapping: dict) -> None:
        """Match edition types with their respective parsers"""
        for _class in cls.__subclasses__():
            if _class.edition_type == "latex_parser":
                _class.get_edition_mapping(mapping)
            else:
                mapping[_class.edition_type] = _class
