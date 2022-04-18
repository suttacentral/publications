"""
These are work models for parsers, which facilitate preparation of publication components and their postprocessing.
Motivation for this is that we often need to iterate over several items from raw data, config data etc.
(for a, b in zip(a_collection, b_collection: ...)).
Also our chain of operations heavily depends on a state of processed components
(i.e. we cannot parse additional preheadings if mainmatter isn't generated;
we cannot create ToC unless mainmatter and additional preheadings are prepared etc...)
Therefore if we wrap all the parsed data (the output of parsers) into objects just like we did with data from API
in pydantic objects, they will be more manageable and would have better control over chain of operations executed
on an object.
"""

from datetime import datetime

from bs4 import Tag
from jinja2 import Template
from pydantic import BaseModel

from sutta_publisher.edition_parsers.helper_functions import generate_html_toc


class MainTableOfContents(BaseModel):
    headings: list[Tag]

    def to_html_str(self, template: Template) -> str:
        return template.render(main_toc=generate_html_toc(self.headings))


class SecondaryTablesOfContents(BaseModel):
    headings: dict[Tag, list[Tag]]

    def to_html_str(self, template: Template) -> dict[Tag, str]:
        tocs: dict[Tag, str] = {}

        for _target, _toc in self.headings.items():
            tocs[_target] = template.render(secondary_toc=generate_html_toc(_toc))

        return tocs


class Volume(BaseModel):
    """Container object for grouping data in processes of transforming from raw payloads from API into output format.

    All fields have None or None-equivalent default values because we start with creating completely empty objects
    and gradually fill the data in a chain of operations.

    The important remark is that the attribute names must match variable names in Jinja templates, because eventually
    they will be passed in as a dictionary to the templates and all non-matching keys will simply be ignored.
    """

    # Per volume metadata
    filename: str = ""
    volume_acronym: str = ""
    volume_isbn: str = ""
    volume_number: int | None = None
    volume_root_title: str = ""
    volume_translation_title: str = ""

    # Content
    main_toc: MainTableOfContents | None = None
    secondary_toc: SecondaryTablesOfContents | None = None
    frontmatter: list[str] = []
    mainmatter: str = ""
    backmatter: list[str] = []

    # Edition metadata (common for all volumes)
    acronym: str = ""
    created: datetime | None = None
    creation_process: str = ""
    creator_biography: str = ""
    creator_name: str = ""
    creator_uid: str = ""
    edition_number: int | None = None
    editions_url: str = ""
    first_published: str = ""
    number_of_volumes: int | None = None
    publication_isbn: str = ""
    publication_number: str = ""
    publication_type: str = ""
    root_name: str = ""
    root_title: str = ""
    source_url: str = ""
    text_description: str = ""
    translation_name: str = ""
    translation_subtitle: str = ""
    translation_title: str = ""
    updated: datetime | None = None

    # def get_printable_values(self) -> dict[str, str | list[str] | int]:
    #     """Returns a dictionary of all"""
    #     output: dict[str, str | int | datetime | list | MainTableOfContents | SecondaryTablesOfContents] = self.__dict__
    #
    #     for _key, _value in output.items():
    #         if isinstance(_value, datetime):
    #             output[_key] = _value.strftime("%Y-%m-%d")
    #         elif isinstance(_value, list):
    #             output[_key] = [str(item) for item in _value]
    #         elif isinstance(_value, (MainTableOfContents, SecondaryTablesOfContents)):
    #             output[_key] = _value.to_html_str()
    #         elif not _value:
    #             output[_key] = ""
    #
    #     return output  # type: ignore


class Edition(BaseModel):
    volumes: list[Volume]
