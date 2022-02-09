import logging

from sutta_publisher.shared.value_objects.results import IngestResult

from .base import Publisher

log = logging.getLogger(__name__)


class HtmlPublisher(Publisher):
    @classmethod
    def publish(cls, result: IngestResult) -> None:
        log.info("** Publishing results: %s", result)
        log.info("** Finished publishing results")
