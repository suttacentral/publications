import logging

from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def publish(result: EditionResult) -> None:
    log.info("Publishing results: %s", result.file_paths)

