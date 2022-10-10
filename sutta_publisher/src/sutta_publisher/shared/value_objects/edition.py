from enum import auto
from pathlib import Path

from pydantic import BaseModel

from .base import StrEnum


class EditionResult(BaseModel):
    file_paths: list[Path]


class EditionType(StrEnum):
    """Edition types that we can create publication for."""

    epub = auto()
    html = auto()
    pdf = auto()
    hardcover = auto()
    paperback = auto()
