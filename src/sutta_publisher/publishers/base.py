from abc import ABC, abstractmethod

from sutta_publisher.shared.value_objects.results import IngestResult


class Publisher(ABC):
    @abstractmethod
    def publish(self, result: IngestResult) -> None:
        pass


class ActivePublishers(tuple):
    """Class for injector to have a bind key."""
