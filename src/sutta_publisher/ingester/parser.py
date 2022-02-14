from abc import ABC, abstractmethod


class BaseParser(ABC):
    """Interface for different types of parsers depending on type of input"""

    ACCEPTED_REFS = ["bj", "pts-vp-pli"]

    @abstractmethod
    def parse_input(self) -> str:
        pass
