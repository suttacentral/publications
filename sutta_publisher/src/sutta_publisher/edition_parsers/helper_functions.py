# mypy: ignore-errors
# TODO: REMOVE MYPY IGNORE
import ast
import os
import re
from collections import namedtuple
from typing import Any, Iterator, cast

import requests
from bs4 import BeautifulSoup, Tag
from ebooklib.epub import Link, Section

from sutta_publisher.shared.value_objects.parser_objects import ToCHeading

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


def process_line(markup: str, segment_id: str, text: str, note: str, references: str, possible_refs: set[str]) -> str:
    # add data-ref attribute to <p>, <ul>, <ol>, <dl> tags (#2417)
    for tag in ["<p", "<ul", "<ol", "<dl"]:
        if tag in markup:
            markup = markup.replace(tag, f"{tag} data-ref='{segment_id}'")

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
    if note:
        text += "<a href='#note-{number}' id='noteref-{number}' role='doc-noteref' epub:type='noteref'>{number}</a>"
    return markup.format(f"{references_html}{text}")


def get_heading_depth(tag: Tag) -> int:
    """Extract heading number from html tag i.e. 'h1' -> 1."""
    return int(re.search(r"^(h)(\d+)$", tag.name).group(2))  # type: ignore


def parse_main_toc_depth(depth: str, html: BeautifulSoup) -> int:
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


def find_sutta_title_depth(html: BeautifulSoup) -> int:
    """Find depth of a header, whose class is 'sutta-title' or 'range-title' when individual suttas have no titles

    Args:
        html: HTML to look for heading with class 'sutta-title' or 'range-title'.
        Only the first found match is processed.

    Returns:
        int: Level of a found heading, None if didn't find any:
    """
    css_class: str = "range-title" if html.find(class_="range-title") else "sutta-title"
    heading: Tag = html.find(name=re.compile(r"^h\d+$"), class_=css_class)
    return get_heading_depth(tag=heading)


def collect_actual_headings(start_depth: int = 1, *, end_depth: int, html: BeautifulSoup) -> list[Tag]:
    """Collect all heading from range h<start_depth>...h<end_depth>

    Args:
        start_depth: Minimal heading depth, the default is h1
        end_depth: Maximal heading depth
        html: A html to search in

    Returns:
        ResultSet: A collection of headings with a specified depth range
    """

    return cast(list[Tag], html.find_all(name=re.compile(rf"^h[{start_depth}-{end_depth}]$")))


def _make_link(tag: Tag, file_name: str) -> Link:
    """Takes id from sutta-title heading tag or parent <article> tag"""
    tag_id = tag.get("id") if tag.get("id") else tag.parent.get("id")
    return Link(href=f"{file_name}#{tag_id}", title=tag.text, uid=tag_id)


def _make_section(tag: Tag, file_name: str) -> Section:
    return Section(title=tag.text, href=f"{file_name}#{tag['id']}")


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


def make_headings_tree(headings: list[ToCHeading]) -> dict[HeadingsIndexTreeFrozen, Tag]:
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
        _update_index(index=heading_index, tag=heading.tag)
        # This freezes and copies the current state of heading_index even though it is used in further iterations
        headings_tree.update({HeadingsIndexTreeFrozen(*heading_index): heading.tag})

    return headings_tree


def make_section_or_link(headings: list[ToCHeading], item: dict | str, file_name: str):
    """Create section (if has children) or link recursively"""
    if headings:
        if isinstance(item, dict) and list(item.keys())[0] == headings[0].uid:
            return [
                _make_section(tag=headings.pop(0).tag, file_name=file_name),
                [make_section_or_link(headings, _item, file_name) for _item in list(item.values())[0]],
            ]
        elif isinstance(item, str) and item == headings[0].uid:
            return _make_link(tag=headings.pop(0).tag, file_name=file_name)


def remove_all_header(headers: list[BeautifulSoup]) -> None:
    """Remove all <header>...</header> tags from HTML (in place), but keep the content"""
    [header.replaceWithChildren() for header in headers]


def remove_all_ul(headers: list[BeautifulSoup]) -> None:
    """Remove all <ul>...</ul> tags from HTML (in place) with their content"""
    [ul.decompose() for ul in [header.find("ul") for header in headers]]


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
    nt = html.new_tag(name=f"h{depth}", id=id_)
    nt.string = text

    return nt


def add_class(tags: list[Tag], class_: str) -> None:
    """Add class to a collection of HTML tags"""
    for tag in tags:
        tag["class"] = tag.get("class", []) + [class_]


def _make_html_link_to_heading(heading: ToCHeading) -> str:
    # Sutta headings contain acronym, translated title and root title span tags. We have to change their css classes
    if heading.type == "leaf":
        span_tags = "".join(str(span).replace("sutta-heading", "toc-item") for span in heading.tag.children)

        return f"<a href='#{heading.uid}'>{span_tags}</a>"

    return f"<a href='#{heading.uid}'>{heading.name}</a>"


def generate_html_toc(headings: list[ToCHeading]) -> str:
    _anchors: list[str] = [_make_html_link_to_heading(heading=heading) for heading in headings]
    _list_items: list[str] = [f"<li>{link}</li>" for link in _anchors]
    _previous_h = 0

    # we need delta level for proper secondary toc indentation
    _delta: int = headings[0].depth - 1 if headings else 0

    toc: list[str] = []
    for _heading, _li in zip(headings, _list_items):
        # If next heading is lower level we open another HTML list for it (to achieve multilevel list in HTML)
        _current_depth = _heading.depth - _delta
        # we come across situation where after h3 (sutta-title) comes preheading (h1),
        # so we need to close both sutta-title nested list and chapters nested list
        _level_difference = abs(_current_depth - _previous_h)
        if _current_depth > _previous_h:
            if toc:
                toc[-1].replace("</li>", "")
            toc.append("<ul>" * _level_difference)
        # If next heading is higher level we close the current HTML list before it
        elif _current_depth < _previous_h:
            toc.append("</ul>" * _level_difference + "</li>")
        toc.append(_li)
        _previous_h = _current_depth

    toc.append("</ul>")

    return "".join(toc)


def extract_string(html: BeautifulSoup) -> str:
    """Retrieve content of the HTML body.
    Useful for converting back and forth between str and HTML (`BeautifulSoup`),
    so that in final concatenated HTML we don't end up with multiple <html>, <head>, <body> tags."""
    tags_to_remove: list[str] = ["html", "head", "body"]
    for attr in tags_to_remove:
        if element := getattr(html, attr, None):
            element.unwrap()
    return cast(str, str(html))
