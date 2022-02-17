from enum import auto
from io import StringIO

from .base import StrEnum


class EditionResult(StringIO):
    pass


class EditionType(StrEnum):
    """Edition types that we can create publication for."""

    epub = auto()
    html = auto()
    pdf = auto()
