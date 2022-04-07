import ast
import os
import re
from collections import namedtuple
from typing import Any, Iterator

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet
from ebooklib.epub import Link, Section

ALL_REFERENCES_URL = os.getenv("ALL_REFERENCES_URL", "")
ACCEPTED_REFERENCES = ast.literal_eval(os.getenv("ACCEPTED_REFERENCES", ""))
MAX_HEADING_DEPTH = 6

HeadingsIndexTreeFrozen = namedtuple(
    "HeadingsIndexTreeFrozen", ["h1", "h2", "h3", "h4", "h5", "h6"]
)  # this is needed for dictionary building, as dictionary keys must be immutable


def fetch_possible_refs() -> set[str]:
    response = requests.get(ALL_REFERENCES_URL)
    jsons_list = response.json()
    irregular_list_of_refs = [json["includes"] for json in jsons_list]
    return set(_flatten_list(irregular_list_of_refs))


def _filter_refs(references: list[tuple[str, str]], accepted_references: list[str]) -> list[tuple[str, str]]:
    """Filter out unaccepted references from a list."""
    return [value for value in references if value[0] in accepted_references]


def _flatten_list(irregular_list: list[Any]) -> list[Any]:
    flat_list = []
    for element in irregular_list:
        if isinstance(element, list):
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list


def _segment_id_to_html(segment_id: str) -> str:
    """Convert segment id strings such as 'mn138:1.5' into HTML anchors."""
    # TODO: [27] Implement logic for toggling visibility of segment ID
    tag = "span"
    displayable: bool = False
    class_ = "class='sc-main'" if displayable else " "
    # Catch two groups. First: 1 or more lowercase letters, second: everything except lowercase letters (one or more)
    regex = re.match(r"^([a-z]+)([^a-z]+)$", segment_id)
    # If not matched, will be None
    if not regex:
        raise KeyError(f"Invalid or unsupported segment ID {segment_id}")
    else:
        segment_id_displayable: str = f"{regex.group(1).upper()} {regex.group(2)}" if displayable else ""
        # Depending on displayable flag return:
        # displayable anchor:                              or non displayable anchor:
        # <a class='sc-main' id='mn138:1.5'>MN 138:1.5</a> or <a id='mn138:1.5'></a>
        return f"<{tag} {class_} id='{segment_id}'>{segment_id_displayable}</{tag}>"


def _split_ref_and_number(reference: str, possible_refs: set[str]) -> tuple[str, str] | None:
    """Split reference strings such as "bj7.1" into tuples e.g. `("bj", "7.1")`."""
    # TODO: [28] Simplify and optimise this function
    # Returns None for each ref type from POSSIBLE_REFS not present in reference string
    matches = [re.match(rf"^({ref_type})(\d+\.?\d*)", reference, flags=re.IGNORECASE) for ref_type in possible_refs]
    try:
        # Select not None value from the list of matches, meaning a ref type is on a list of possible refs
        match = [match for match in matches if match][0]
        return match.group(1), match.group(2)
    except IndexError:  # string doesn't match any of the POSSIBLE_REFs
        return None


def _reference_to_html(reference: tuple[str, str]) -> str:
    """Return HTML element made of a reference tuple i.e. `("bj", "7,9")`."""
    ref_type, ref_id = reference
    # E.g. <a class='bj' id='bj7.2'>BJ 7.2</a>
    return f"<a class='{ref_type}' id='{ref_type}{ref_id}'>{ref_type.upper()} {ref_id}</a>"


def process_a_line(markup: str, segment_id: str, text: str, references: str, possible_refs: set[str]) -> str:
    segment_id_html: str = _segment_id_to_html(segment_id)
    # references are passed as a string such as: "ref1, ref2, ref3"
    split_references: list[str] = [r.strip() for r in references.split(",")]
    references_divided_into_types_and_ids: list[tuple[str, str] | None] = [
        _split_ref_and_number(reference=ref, possible_refs=possible_refs) for ref in split_references
    ]

    filtered_references = [ref for ref in references_divided_into_types_and_ids if ref]
    # filter out unaccepted references
    filtered_references = _filter_refs(references=filtered_references, accepted_references=ACCEPTED_REFERENCES)
    list_of_refs_tags: list[str] = [_reference_to_html(reference) for reference in filtered_references]
    references_html = "".join(list_of_refs_tags)
    return markup.format(f"{segment_id_html}{references_html}{text}")


def get_heading_depth(tag: Tag) -> int:
    """Extract heading number from html tag i.e. 'h1' -> 1."""
    return int(re.search(r"^(h)(\d+)$", tag.name).group(2))  # type: ignore


def _parse_main_toc_depth(depth: str, html: BeautifulSoup) -> int:
    """Analyse data from config.edition.main_toc_depth and return actual number hor heading depth for ToC.

    Args:
        depth: depth of ToC headings tree provided as: "all" | "1" | "2".
        html: HTML of a single volume/chapter

    Returns:
        int: A level of a found heading
    """
    if depth == "all":  # Means ToC goes down from h1 to hX with class='sutta-title'
        return find_sutta_title_depth(html)
    else:  # Else depth given explicitly.ToC made of h1...h<depth> range of headings
        return int(re.match(rf"^[1-{depth}]$", depth).group(0))  # type: ignore


def collect_main_toc_depths(depth: str, all_volumes: list[BeautifulSoup]) -> list[int]:
    """Collect ToC depths for all volumes.

    Args:
        depth: unparsed input from configuration (such as: "all", "1")
        all_volumes: HTML for each volume

    Returns:
        list[int]: list of depths for each volume
    """
    return [_parse_main_toc_depth(depth=depth, html=volume) for volume in all_volumes]


def collect_secondary_toc_depths(main_toc_depths: list[int], all_volumes: list[BeautifulSoup]) -> list[tuple[int, int]]:
    """Collect depths range for secondary ToCs as (start_depth, end_depth)"""
    toc_ranges: list[tuple[int, int]] = []
    for _main_toc, _volume in zip(main_toc_depths, all_volumes):
        # Secondary ToC always starts one level below deepest main ToC heading
        # Secondary ToC always ends on level of heading with class 'sutta-title'
        toc_ranges.append((_main_toc + 1, find_sutta_title_depth(_volume)))

    return toc_ranges


def find_sutta_title_depth(html: BeautifulSoup) -> int:
    """Find depth of a header, whose class is 'sutta-title'

    Args:
        html: HTML to look for heading with class 'sutta-title'. Only the first found match is processed

    Returns:
        int: Level of a found heading, None if didn't find any:
    """
    heading: Tag = html.find(name=re.compile(r"^h\d+$"), class_="sutta-title")
    return get_heading_depth(tag=heading)


def collect_actual_headings(start_depth: int = 1, *, end_depth: int, volume: BeautifulSoup) -> ResultSet:
    """Collect all heading from range h<start_depth>...h<end_depth>

    Args:
        start_depth: Minimal heading depth, the default is h1
        end_depth: Maximal heading depth
        volume: A html to search in

    Returns:
        ResultSet: A collection of headings with a specified depth range
    """

    return volume.find_all(name=re.compile(rf"^h[{start_depth}-{end_depth}]$"))


def _make_link(tag: Tag, file_name: str) -> Link:
    return Link(href=f"{file_name}#{tag.span['id']}", title=tag.text, uid=tag.span["id"])


def _make_section(tag: Tag, file_name: str) -> Section:
    return Section(title=tag.text, href=f"{file_name}#{tag.span['id']}")


def _nest_or_extend(headings: Iterator[Tag], file_name: str) -> Link | list | None:
    """Recursively build a nested links and sections structure ready to be used for epub ToC

    Args:
        headings:
        file_name:

    Returns:
        Link | list | None:

    """
    current_tag = next(headings, None)
    next_tag = next(headings, None)

    if not current_tag:
        return None  # reached the end of list
    elif not next_tag or get_heading_depth(current_tag) <= get_heading_depth(next_tag):
        return _make_link(tag=current_tag, file_name=file_name)
    else:  # next heading is lower level, need to nest
        return [_make_section(tag=current_tag, file_name=file_name), [_nest_or_extend(headings, file_name)]]


def _update_index(index: list[int], tag: Tag) -> None:
    """Increment index for this heading level **IN PLACE**

    e.g. [1, 1, 2+1, 0, 0, 0] - added another h3
    """
    index[get_heading_depth(tag) - 1] += 1

    # When adding another heading all lower level headings counters are reset
    for i in range(get_heading_depth(tag), 6):
        index[i] = 0


def _find_index_root(index: HeadingsIndexTreeFrozen) -> tuple[int, ...]:
    """Find common index root for all children of this heading - i.e. a non-zero subset of this tuple"""
    return tuple([i for i in index if i != 0])


def _compare_index_with_root(index: HeadingsIndexTreeFrozen, root: tuple[int, ...]) -> bool:
    """Return True if index is in a given root (heading is a child of superheading with that root)"""
    for i, counter in enumerate(root):
        if counter != index[i]:
            return False
    return True


def find_children_by_index(
    index: HeadingsIndexTreeFrozen, headings_tree: dict[HeadingsIndexTreeFrozen, Tag]
) -> list[HeadingsIndexTreeFrozen]:
    """Based on parents index, find all children and return their indices"""
    parent_root = _find_index_root(index)
    # Return all indexes with the same root except for the parent
    return [
        child_index
        for child_index in headings_tree.keys()
        if _compare_index_with_root(index=child_index, root=parent_root) and child_index != index
    ]


def make_headings_tree(headings: list[Tag]) -> dict[HeadingsIndexTreeFrozen, Tag]:
    """Build a tree of headings where structure is represented by tuple of indexes

    Args:
        headings: list of headings to create a tree of

    Returns:
        dict[tuple,  list[Tag]]: a structure of headings as index: heading
    """
    heading_index = [0, 0, 0, 0, 0, 0]

    # Build a tree of headings where structure is represented by tuple of indexes
    headings_tree: dict[HeadingsIndexTreeFrozen, Tag] = {}
    for heading in headings:
        _update_index(index=heading_index, tag=heading)
        # This freezes and copies the current state of heading_index even though it is used in further iterations
        headings_tree.update({HeadingsIndexTreeFrozen(*heading_index): heading})

    return headings_tree


def make_section_or_link(
    index: HeadingsIndexTreeFrozen, headings_tree: dict[HeadingsIndexTreeFrozen, Tag], file_name: str
) -> list[Section] | Link:
    """Look up heading's children and accordingly create link or section recursively"""
    children: list[HeadingsIndexTreeFrozen] = find_children_by_index(index=index, headings_tree=headings_tree)
    heading: Tag = headings_tree[index]
    # Heading has children (subheadings), so it's a Section
    if children:
        return [
            _make_section(tag=heading, file_name=file_name),
            [make_section_or_link(index=child, headings_tree=headings_tree, file_name=file_name) for child in children],
        ]
    # Heading is childless so it's a Link
    else:
        return _make_link(tag=heading, file_name=file_name)


def remove_all_ul(html: BeautifulSoup) -> None:
    """Remove all <ul>...</ul> tags from HTML (in place)"""
    [ul.decompose() for ul in html.find_all("ul")]


def increment_heading_by_number(by_number: int, heading: Tag) -> None:
    """Increases an HTML heading depth by number e.g. h2 -> h4 (in place)"""

    current_depth = get_heading_depth(heading)
    heading.name = f"h{current_depth + by_number}"


def find_all_headings(html: BeautifulSoup) -> list[Tag]:
    """Get a list of all hX element from HTML"""
    return list(html.find_all(name=re.compile(r"h\d+")))


def create_html_heading_with_id(html: BeautifulSoup, *, depth: int, text: str, id_: str) -> Tag:
    """Create new tag of format:  <h1><span id="some-id"></span>Some Title</h1>,

    Args:
        html: an HTML, for which to build a heading
        depth: a depth of heading e.g. 1 for "h1", 2 for "h2" etc.
        text: a title for the heading
        id_: an id property to assign to the new tag

    Returns:
        Tag: an HTML tag with id ready to insert
    """
    nt = html.new_tag(name=f"h{depth}")
    nt.string = text

    nt_inner = html.new_tag(name="span", id=id_)
    nt.insert(position=0, new_child=nt_inner)

    return nt


def add_class(tags: list[Tag], class_: str) -> None:
    """Sdd class to a collection of HTML tags"""
    for tag in tags:
        tag["class"] = tag.get("class", []) + [class_]


def make_html_link_to_heading(tag: Tag) -> str:
    return f"<a href='#{tag.span.get('id')}'>{tag.text}</a>"
