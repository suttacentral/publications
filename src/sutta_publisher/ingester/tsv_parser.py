from os import PathLike

import pandas as pd
from pandas._typing import ReadCsvBuffer

from sutta_publisher.ingester.helper_functions import (
    _catch_translation_en_column,
    _reference_to_html,
    _segment_id_to_html,
    _split_html_on_bracket,
    _split_ref_and_number,
)
from sutta_publisher.ingester.parser import BaseParser


class TsvParser(BaseParser):
    def __init__(self, tsv: str | PathLike[str] | ReadCsvBuffer[bytes] | ReadCsvBuffer[str]) -> None:
        self.spreadsheet = pd.read_csv(tsv, sep="\t", header=0)
        # columns with translations have translator's name in it (eg. translation-en-sujato) so we need regex to find English translation
        en = _catch_translation_en_column(self.spreadsheet.columns)
        self.spreadsheet = self.spreadsheet[[en, "html", "reference", "segment_id"]]
        self.spreadsheet.rename(columns={en: "english"}, inplace=True)
        self.spreadsheet.fillna("")  # replace empty cells with empty strings, so we can assume all input has str

    def parse_input(self) -> str:
        """Parse a tsv spreadsheet content and construct HTML string"""
        # TODO: replace with Jinja2 template
        # Only construct the body of a page here
        output = ""
        # TODO: look for more efficient method for dataframes than looping
        for _, row in self.spreadsheet.iterrows():
            html: list[str] = _split_html_on_bracket(row["html"])
            split_ref: tuple[str, str] = _split_ref_and_number(row["reference"])
            reference: str = _reference_to_html(split_ref) if split_ref else ""
            segment_id = _segment_id_to_html(row["segment_id"])
            # e.g.      <p><a class='sc-main' id='dn1:1.10.16'>DN 1:1.10.16</a>‘He refrains from running errands...<a id='dn1:1.10.17'></a></p>
            output += f"{html[0]}{reference}{row['english']}{segment_id}{html[1]}"
        return output
