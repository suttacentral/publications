from __future__ import annotations

from typing import Iterator

from pydantic import BaseModel

from .edition import EditionType


class VolumeDetail(BaseModel):
    endmatter: list[str]
    frontmatter: list[str]
    mainmatter: list[str]


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
    created: str
    updated: str
    working_dir: str
    main_toc_depth: str
    secondary_toc: bool

    class Config:
        extra = "ignore"


class PublicationDetails(BaseModel):
    creator_name: str
    translation_subtitle: str
    translation_title: str
    translation_lang_iso: str

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
