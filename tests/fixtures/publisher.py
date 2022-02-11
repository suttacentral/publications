from sutta_publisher.publishers.base import Publisher
from sutta_publisher.shared.value_objects.results import IngestResult


class TestPublisher(Publisher):
    published_output: str = ""

    def publish(self, result: IngestResult) -> None:
        self.published_output = result.content
