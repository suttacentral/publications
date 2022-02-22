import re
from typing import Any, cast

import requests

ALL_REFERENCES_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/misc/pali_reference_edition.json"
ACCEPTED_REFERENCES = ["bj", "pts-vp-pli"]


def _fetch_possible_refs() -> list[str]:
    response = requests.get(ALL_REFERENCES_URL)
    jsons_list = response.json()
    irregular_list_of_refs = [json["includes"] for json in jsons_list]
    # Flatten list of strings and lists
    return _flatten_list(irregular_list_of_refs)


def _filter_refs(references: list[tuple[str, str]], accepted_references: list[str]) -> list[tuple[str, str]]:
    """Filters out not accepted references from a list"""
    return [value for value in references if value[0] in accepted_references]


def _flatten_list(irregular_list: list[Any]) -> list[Any]:
    flat_list = []
    # Iterate through the outer list
    for element in irregular_list:
        if type(element) is list:
            # If the element is of type list, iterate through the sublist
            for item in element:
                flat_list.append(item)
        else:
            flat_list.append(element)
    return flat_list


def _segment_id_to_html(segment_id: str) -> str:
    """Convert segment id strings such as 'mn138:1.5' into displayable format such as: 'MN 138:1.5'"""
    # TODO: add logic for when to display and when not to display segment ID
    displayable: bool = True  # ?????
    class_ = " class='sc-main' " if displayable else " "
    # Catch two groups. First: 1 or more lowercase letters, second: everything except lowercase letters (one or more)
    regex = re.match("^([a-z]+)([^a-z]+)$", segment_id)
    # If not matched will be None
    if not regex:
        raise KeyError(f"Invalid or unsupported segment ID {segment_id}")
    else:
        segment_id_displayable: str = f"{regex.group(1).upper()} {regex.group(2)}" if displayable else ""
        # Depending on displayable flag return:
        # displayable anchor:                              or non displayable anchor:
        # <a class='sc-main' id='mn138:1.5'>MN 138:1.5</a> or <a id='mn138:1.5'></a>
        return f"<a{class_}id='{segment_id}'>{segment_id_displayable}</a>"


def _split_ref_and_number(reference: str, possible_refs: list[str]) -> tuple[str, str] | None:
    """Split reference strings such as "bj7.1" into tuples e.g. ("bj", "7.1")"""
    # We use possible_refs list fetched from GitHub because the references have inconsistent formats, letters, numbers, hyphens, dots...
    # It's hard to guess which part is "reference type" (e.g. bj) and which is "reference id" (e.g. 7.9).
    # This is what I called them, not the official names
    # Additional benefit (although we could do away without it) is that we can also valide the references received in a payload against a list of possible references

    # Returns None for each ref type from POSSIBLE_REFS not present in reference string
    matches = [re.match(rf"^({ref_type})(\d+\.?\d*)", reference, flags=re.IGNORECASE) for ref_type in possible_refs]
    try:
        # Select not None value from the list of matches, meaning a ref type is on a list of possible refs
        match = [match for match in matches if match][0]
        # Build tuple consisting of (ref_type, ref_id) e.g. ("bj", "7.1")
        return match.group(1), match.group(2)
    except IndexError:  # string doesn't match any of the POSSIBLE_REFs
        return None


def _reference_to_html(reference: tuple[str, str]) -> str:
    """Return HTML element made of a reference tuple i.e. ("bj", "7,9")"""
    # First make a tuple: (ref_type, ref_id)
    ref_type, ref_id = reference
    # E.g. <a class='bj' id='bj7.2'>BJ 7.2</a>
    return f"<a class='{ref_type}' id='{ref_type}{ref_id}'>{ref_type.upper()} {ref_id}</a>"


# TODO: verify if we still need this. This was used in TsvParser
def _catch_translation_en_column(column_names: list[str]) -> str | None:
    """Given a list of columns in a tsv file return a column with English translation"""
    # Check a list of column names against a pattern. Get a list of lists with matches (or list of empty lists)
    columns_matches = [re.findall(pattern=r"^translation-en-.*", string=column) for column in column_names]
    # If list evaluates
    try:
        return cast(str, [column for column in columns_matches if column][0][0])
    except IndexError:
        # No column with English translation (or name doesn't match the pattern)
        return None


def _process_a_line(markup: str, segment_id: str, text: str, references: str, possible_refs: list[str]) -> str:
    segment_id_html: str = _segment_id_to_html(segment_id)  # create html tag from segment_id
    split_references: list[str] = references.split(
        ", "
    )  # references are passed as a string such as: "ref1, ref2, ref3"
    references_divided_into_types_and_ids: list[tuple[str, str] | None] = [
        _split_ref_and_number(reference=ref, possible_refs=possible_refs) for ref in split_references
    ]
    filtered_references = [ref for ref in references_divided_into_types_and_ids if ref]  # filter out Nones
    filtered_references = _filter_refs(
        references=filtered_references, accepted_references=ACCEPTED_REFERENCES
    )  # filter out unaccepted references
    list_of_refs_tags: list[str] = [_reference_to_html(reference) for reference in filtered_references]
    references_html = "".join(list_of_refs_tags)
    return markup.format(f"{segment_id_html}{references_html}{text}")
