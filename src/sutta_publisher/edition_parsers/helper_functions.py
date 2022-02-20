import re
from typing import Any, cast

import requests

ALL_REFERENCES_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/misc/pali_reference_edition.json"


def _fetch_possible_refs() -> list[str]:
    response = requests.get(ALL_REFERENCES_URL)
    jsons_list = response.json()
    irregular_list_of_refs = [json["includes"] for json in jsons_list]
    # Flatten list of strings and lists
    return _flatten_list(irregular_list_of_refs)


def _filter_refs(refs: list[str], accepted_refs: list[str]) -> list[str]:
    """Filters out not accepted references from a list"""
    return [value for value in refs if value in accepted_refs]


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


def _split_ref_and_number(reference: str | None, possible_refs: list[str]) -> tuple[str, str] | None:
    """Split reference strings such as "bj7.1" into tuples e.g. ("bj", "7.1")"""
    # We work on a full dataframe column so nan is possible:
    if type(reference) is not str:
        return None
    else:
        # Returns None for each ref type from POSSIBLE_REFS not present in reference string
        matches = [re.match(rf"^({ref_type})(\d+\.?\d*)", reference, flags=re.IGNORECASE) for ref_type in possible_refs]
        try:
            # Select not None value from the list of matches
            match = [match for match in matches if match][0]
            # Build tuple consisting of (ref_type, ref_id) e.g. ("bj", "7.1")
            return match.group(1), match.group(2)
        except IndexError:  # string doesn't match any of the POSSIBLE_REFs
            return None


def _reference_to_html(reference: tuple[str, str]) -> str:
    """Return HTML element made of a reference"""
    ref_type, ref_id = reference
    # E.g. <a class='bj' id='bj7.2'>BJ 7.2</a>
    return f"<a class='{ref_type}' id='{ref_type}{ref_id}'>{ref_type.upper()} {ref_id}</a>"


def _segment_id_to_html(segment_id: str) -> str:
    return f"<a id='{segment_id}'></a>"


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


def _remove_multiple_white_characters(text: str) -> str:
    """Return a new string with all whitespaces substituted with a single space"""
    return re.sub(r"\s{2,}", " ", text)
