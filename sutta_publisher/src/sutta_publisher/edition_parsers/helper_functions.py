import re
from typing import Any, cast

import requests
from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet

ALL_REFERENCES_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/misc/pali_reference_edition.json"
ACCEPTED_REFERENCES = ["bj", "pts-vp-pli"]
MAX_HEADING_DEPTH = 6


def _fetch_possible_refs() -> list[str]:
    response = requests.get(ALL_REFERENCES_URL)
    jsons_list = response.json()
    irregular_list_of_refs = [json["includes"] for json in jsons_list]
    return _flatten_list(irregular_list_of_refs)


def _filter_refs(references: list[tuple[str, str]], accepted_references: list[str]) -> list[tuple[str, str]]:
    """Filters out unaccepted references from a list"""
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
    """Convert segment id strings such as 'mn138:1.5' into HTML anchors"""
    # TODO: [#27] Implement logic for toggling visibility of segment ID
    tag = "span"
    displayable: bool = False
    class_ = "class='sc-main'" if displayable else " "
    # Catch two groups. First: 1 or more lowercase letters, second: everything except lowercase letters (one or more)
    regex = re.match("^([a-z]+)([^a-z]+)$", segment_id)
    # If not matched, will be None
    if not regex:
        raise KeyError(f"Invalid or unsupported segment ID {segment_id}")
    else:
        segment_id_displayable: str = f"{regex.group(1).upper()} {regex.group(2)}" if displayable else ""
        # Depending on displayable flag return:
        # displayable anchor:                              or non displayable anchor:
        # <a class='sc-main' id='mn138:1.5'>MN 138:1.5</a> or <a id='mn138:1.5'></a>
        return f"<{tag} {class_} id='{segment_id}'>{segment_id_displayable}</{tag}>"


def _split_ref_and_number(reference: str, possible_refs: list[str]) -> tuple[str, str] | None:
    """Split reference strings such as "bj7.1" into tuples e.g. ("bj", "7.1")"""
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
    """Return HTML element made of a reference tuple i.e. ("bj", "7,9")"""
    ref_type, ref_id = reference
    # E.g. <a class='bj' id='bj7.2'>BJ 7.2</a>
    return f"<a class='{ref_type}' id='{ref_type}{ref_id}'>{ref_type.upper()} {ref_id}</a>"


def _process_a_line(markup: str, segment_id: str, text: str, references: str, possible_refs: list[str]) -> str:
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


def _get_heading_number(heading_tag: Tag) -> int:
    """Extract heading number from html tag i.e. 'h1' -> 1"""
    return int(re.search(f"^(h)([1-{MAX_HEADING_DEPTH}])$", heading_tag.name).group(2))  # type: ignore


def _parse_main_toc_depth(depth: str, html: BeautifulSoup) -> int:
    """Analyse data from config.edition.main_toc_depth and return actual number hor heading depth for ToC

    Args:
        depth: depth of ToC headings tree provided as: "all" | "1" | "2".
        html: HTML of a single volume/chapter

    Returns:
        int: A level of a found heading
    """
    if depth == "all":  # Means ToC goes down from h1 to hX with class='sutta-title'
        return _find_sutta_title_depth(html)
    else:  # Else depth given explicitly.ToC made of h1...h<depth> range of headings
        return int(re.match(f"^[1-{depth}]$", depth).group(0))  # type: ignore


def collect_main_toc_depths(depth: str, all_volumes: list[BeautifulSoup]) -> list[int]:
    """Collect ToC depths for all volumes"""
    return [_parse_main_toc_depth(depth=depth, html=volume) for volume in all_volumes]


def _find_sutta_title_depth(html: BeautifulSoup) -> int:
    """Find depth of a header, whose class is 'sutta-title'

    Returns:
        Level of a found heading, None if didn't find any:
    """
    heading: Tag = html.find(name=re.compile(f"^h[1-{MAX_HEADING_DEPTH}]"), class_="sutta-title")
    return _get_heading_number(heading_tag=heading)


def _collect_headings(start_depth: int = 1, *, end_depth: int, volume: BeautifulSoup) -> ResultSet:
    """Collect all heading from range h<start_depth>...h<end_depth>

    Args:
        start_depth: Minimal heading depth, the default is h1
        end_depth: Maximal heading depth
        volume: A html to search in

    Returns:
        ResultSet: A collection of headings with a specified depth range
    """
    return cast(ResultSet, volume.find_all(name=re.compile(f"^h[{start_depth}-{end_depth}]$")))
