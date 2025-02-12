from __future__ import annotations

import datetime
import logging
from typing import Iterator, Literal, Optional

from pydantic import BaseModel, validator

from sutta_publisher.shared.edition_finder import find_edition_ids
from sutta_publisher.shared.github_handler import update_run_date
from sutta_publisher.shared.value_objects.edition import EditionType

log = logging.getLogger(__name__)


class VolumeDetail(BaseModel):
    volume_blurb: str | None
    volume_number: str | None
    volume_isbn: str | None
    volume_acronym: str | None
    volume_translation_title: str | None
    volume_root_title: str | None
    backmatter: list[str]
    frontmatter: list[str]
    mainmatter: list[str]

    @validator("volume_blurb", "volume_number", "volume_isbn", "volume_acronym", pre=True)
    def sanitize_input(cls, field: Literal[False] | str) -> str:
        if field is False:
            return ""
        else:
            return field


class Volumes(BaseModel):
    __root__: list[VolumeDetail]

    def __len__(self) -> int:
        return len(self.__root__)

    def __iter__(self) -> Iterator[VolumeDetail]:  # type: ignore
        return iter(self.__root__)

    def __getitem__(self, item: int) -> VolumeDetail:
        return self.__root__[item]


class EditionDetails(BaseModel):
    cover_bleed: str | None
    cover_theme_color: str | None
    created: str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    edition_id: str
    edition_number: str
    main_toc_depth: str
    noteref_id: int = 0  # Helper field for proper numbering of note references in editions with multiple volumes
    number_of_volumes: int
    page_height: str | None
    page_width: str | None
    publication_blurb: str | None
    publication_isbn: str
    publication_number: str
    publication_type: EditionType
    secondary_toc: bool
    updated: Optional[
        str
    ]  # Upon the first publication we leave it uninitialized. This will only be initialized/changed when further changes are introduced.
    volumes: Volumes
    working_dir: str
    text_uid: str

    @validator("cover_bleed", "publication_blurb", pre=True)
    def sanitize_input(cls, field: Literal[False] | str) -> str:
        if field is False:
            return ""
        else:
            return field

    class Config:
        extra = "ignore"


class PublicationDetails(BaseModel):
    creation_process: str
    creator_name: str
    creator_uid: str
    creator_bio: str | None = None
    first_published: str
    root_lang_name: str
    root_title: str
    source_url: str
    text_description: str
    translation_lang_iso: str
    translation_lang_name: str
    translation_subtitle: str
    translation_title: str

    class Config:
        extra = "ignore"


class EditionConfig(BaseModel):
    edition: EditionDetails
    publication: PublicationDetails

    class Config:
        extra = "ignore"  # Ignore undefined fields


class EditionMappingList(BaseModel):
    """Mapping between `publication_number` and `edition_id`."""

    __root__: list[dict[str, str]]

    def get_edition_ids(self, publication_numbers: list[str]) -> list[str]:
        """
        Get edition ids for given publications.
        Raise `ValueError` when there are no editions for these publications.
        """
        edition_ids = (
            entry["edition_id"] for entry in self.__root__ if entry["publication_number"] in publication_numbers
        )
        editions: list[str] = sorted(edition_ids)
        if not editions:
            raise ValueError(f"No editions found for {publication_numbers=}.")
        return editions

    def auto_find_edition_ids(self, api_key: str) -> list[str]:
        edition_ids: list[str] = find_edition_ids(data=self.__root__, api_key=api_key)

        if not edition_ids:
            logging.info(f"Publications are up-to-date.")
            update_run_date(api_key)
            raise SystemExit()

        return edition_ids


class EditionsConfigs(list[EditionConfig]):
    """List the editions configs for a given publication."""

    def get_edition(self, edition: EditionType) -> EditionConfig:
        """Get specific edition type. Handy to fish-out config for publisher."""
        for edition_cfg in self:
            if edition_cfg.edition.publication_type == edition:
                return edition_cfg
        raise KeyError(f"{edition=} not found.")
