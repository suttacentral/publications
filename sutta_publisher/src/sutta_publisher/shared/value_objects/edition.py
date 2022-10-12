from enum import auto
from pathlib import Path

from pydantic import BaseModel

from .base import StrEnum


class EditionResult(BaseModel):
    # List of result file paths for each volume
    volumes: list[list[Path]]

    creator_uid: str
    publication_type: str
    text_uid: str
    translation_lang_iso: str


class EditionType(StrEnum):
    """Edition types that we can create publication for."""

    epub = auto()
    html = auto()
    pdf = auto()
    hardcover = auto()
    paperback = auto()
