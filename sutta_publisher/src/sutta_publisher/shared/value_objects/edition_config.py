from __future__ import annotations

import datetime
from typing import Iterator, Literal, Optional

from pydantic import BaseModel, validator

from .edition import EditionType


class VolumeDetail(BaseModel):
    volume_number: str | None
    volume_isbn: str | None
    volume_acronym: str | None
    volume_translation_title: str | None
    volume_root_title: str | None
    backmatter: list[str]
    frontmatter: list[str]
    mainmatter: list[str]

    @validator("volume_number", "volume_isbn", "volume_acronym", pre=True)
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
    edition_id: str
    publication_number: str
    publication_type: EditionType
    volumes: Volumes
    created: str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    updated: Optional[
        str
    ]  # Upon the first publication we leave it uninitialized. This will only be initialized/changed when further changes are introduced.
    working_dir: str
    main_toc_depth: str
    secondary_toc: bool
    edition_number: str
    publication_isbn: str
    noteref_id: int = 0  # Helper field for proper numbering of note references in editions with multiple volumes
    text_uid: str

    class Config:
        extra = "ignore"


class PublicationDetails(BaseModel):
    creator_name: str
    creator_uid: str
    creator_bio: str | None = None
    translation_subtitle: str
    translation_title: str
    translation_lang_iso: str
    creation_process: str
    first_published: str
    root_lang_name: str
    root_title: str
    source_url: str
    text_description: str
    translation_lang_name: str

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

    def get_editions_id(self, publication_number: str) -> list[str]:
        """
        Get editions id for a given publication.
        Raise `ValueError` when there are no editions for that publication.
        """
        editions_ids = (
            entry["edition_id"] for entry in self.__root__ if entry["publication_number"] == publication_number
        )
        editions: list[str] = sorted(editions_ids)
        if not editions:
            raise ValueError(f"No editions found for {publication_number=}.")
        return editions


class EditionsConfigs(list[EditionConfig]):
    """List the editions configs for a given publication."""

    def get_edition(self, edition: EditionType) -> EditionConfig:
        """Get specific edition type. Handy to fish-out config for publisher."""
        for edition_cfg in self:
            if edition_cfg.edition.publication_type == edition:
                return edition_cfg
        raise KeyError(f"{edition=} not found.")
