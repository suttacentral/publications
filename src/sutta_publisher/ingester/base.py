import logging

import inject

from sutta_publisher.ingester.parser import BaseParser
from sutta_publisher.shared.config import Config
from sutta_publisher.shared.value_objects.results import IngestResult

log = logging.getLogger(__name__)


class Ingester:
    config: Config = inject.attr(Config)

    @classmethod
    def get_result(cls, parser: BaseParser) -> IngestResult:
        log.info("** Running conversion for publication: %s", cls.config.publication_number)
        # TODO: discuss design with the team
        parser.parse_input()
        result = IngestResult(content=f"<html><body>{cls.config.publication_number=}</body></html>")
        log.info("** Finished conversion for publication: %s", cls.config.publication_number)
        return result
