import re
from pathlib import PurePath
from typing import Mapping

import pandas as pd

POSSIBLE_REFS = ["bj", "pts-vp-pli"]
ACCEPTED_REFS = ["bj", "pts-vp-pli"]


def _split_ref_and_number(reference: str) -> tuple[str, str] | None:
    """Split reference strings such as "bj7.1" into tuples e.g. ("bj", "7.1")"""
    # Returns None for each ref type from POSSIBLE_REFS not present in reference string
    matches = [re.match(rf"^({ref_type})(\d+\.?\d*)", reference, flags=re.IGNORECASE) for ref_type in POSSIBLE_REFS]
    try:
        # Select the not None value from the list of matches
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


def _write_to_file(content: str, filepath: PurePath) -> None:
    with open(filepath, "w") as f:
        f.write(content)


def _catch_translation_en_column(column_names: list[str]) -> str | None:
    """Given a list of columns in a tsv file return a column with English translation"""
    # Check a list of column names against a pattern. Get a list of lists with matches (or list of empty lists)
    columns_matches = [re.findall(pattern=r"^translation-en-.*\|", string=column) for column in column_names]
    # If list evaluates
    try:
        return [column for column in columns_matches if column][0][0]
    except IndexError:
        # No column with English translation (or name doesn't match the pattern)
        return None


def tsv_to_html(tsv: PurePath) -> None:
    spreadsheet = pd.read_csv(tsv, sep='\t', header=0)
    # columns with translations have translator's name in it (eg. translation-en-sujato) so we need regex to find English translation
    en = _catch_translation_en_column(spreadsheet.columns)
    spreadsheet = spreadsheet[["segment_id", en, "html", "reference"]]

    _write_to_file(...)


def json_to_html(json: Mapping[str, str]) -> str:
    pass
