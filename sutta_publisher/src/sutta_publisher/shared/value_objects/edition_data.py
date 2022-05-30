from dataclasses import dataclass
from typing import Iterator, Optional

from pydantic import BaseModel, Field


class Heading(BaseModel):
    heading_id: str = Field(alias="uid")


class HeadingsGroup(list[Heading]):
    """A group of leafs nodes that come after preheadings (usually chapter titles)"""


class MainMatterHeadings(list[HeadingsGroup]):
    """This is a collection of headings for a whole mainmatter (all headings for a single uid)"""


class VolumeHeadings(list[MainMatterHeadings]):
    """This is a collection of headings for a whole volume (all headings for a single uid)"""


class Preheading(BaseModel):
    uid: str
    name: str


class PreheadingsGroup(list[Preheading]):
    """This is a collection of preheadings for a single 'leaf' - partial mainmatter"""


class MainMatterPreheadings(list[PreheadingsGroup]):
    """This is a collection of preheadings for a whole mainmatter (all preheadings for a single uid)"""


class VolumePreheadings(list[MainMatterPreheadings]):
    """This is a collection of preheadings for a whole volume"""


class EditionPreheadings(list[VolumePreheadings]):
    """We need to return data for each volume separately."""


class NodeDetails(BaseModel):
    main_text: Optional[dict[str, str]]
    markup: Optional[dict[str, str]]
    notes: Optional[dict[str, str]]
    reference: Optional[dict[str, str]]


class Node(BaseModel):
    acronym: Optional[str]
    blurb: Optional[str]
    mainmatter: NodeDetails
    name: str
    root_name: Optional[str]
    type: str
    uid: str


class MainMatterPart(BaseModel):
    __root__: list[Node]

    def __len__(self) -> int:
        return len(self.__root__)

    def __iter__(self) -> Iterator[Node]:  # type: ignore
        return iter(self.__root__)

    def __getitem__(self, item: int) -> Node:
        return self.__root__[item]


class MainMatter(BaseModel):
    __root__: list[MainMatterPart]

    def __len__(self) -> int:
        return len(self.__root__)

    def __iter__(self) -> Iterator[MainMatterPart]:  # type: ignore
        return iter(self.__root__)

    def __getitem__(self, item: int) -> MainMatterPart:
        return self.__root__[item]


@dataclass
class VolumeData:
    preheadings: VolumePreheadings
    headings: VolumeHeadings
    # Return the mainmatter for a volume mainmatter
    mainmatter: MainMatter

    # `extras` - return all files that pertain to an edition as key:value pairs,
    # where the key is the filename as found in the config (these
    # work as unique identifiers) and the value is a string, either
    # raw HTML for .html files, or base64 for .jpg/.png
    extras: dict[str, str]
    acronym: str = ""


class EditionData(list[VolumeData]):
    """We need to return data for each volume separately."""
