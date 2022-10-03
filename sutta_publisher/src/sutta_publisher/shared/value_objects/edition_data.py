from dataclasses import dataclass
from typing import Iterator, Optional

from pydantic import BaseModel


class NodeDetails(BaseModel):
    main_text: Optional[dict[str, str]]
    markup: Optional[dict[str, str]]
    notes: Optional[dict[str, str]]
    reference: Optional[dict[str, str]]


class Node(BaseModel):
    acronym: Optional[str]
    blurb: Optional[str]
    mainmatter: NodeDetails
    name: Optional[str]
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
    # Return the mainmatter for a volume mainmatter
    mainmatter: MainMatter
    tree: list[dict | str]
    depths: dict[str, int]

    # `extras` - return all files that pertain to an edition as key:value pairs,
    # where the key is the filename as found in the config (these
    # work as unique identifiers) and the value is a string, either
    # raw HTML for .html files, or base64 for .jpg/.png
    extras: dict[str, str]


class EditionData(list[VolumeData]):
    """We need to return data for each volume separately."""
