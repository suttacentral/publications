import logging

import inject

from sutta_publisher.ingester.tsv_parser import TsvParser
from sutta_publisher.shared.config import Config
from sutta_publisher.shared.value_objects.results import IngestResult

log = logging.getLogger(__name__)


class Ingester:
    config: Config = inject.attr(Config)

    @classmethod
    def get_result(cls) -> IngestResult:
        log.info("** Running conversion for publication: %s", cls.config.publication_number)
        parser = TsvParser(cls.config.input_path)
        result = IngestResult(content=f"{parser.parse_input()}\n<p>{cls.config.publication_number=}</p>")
        log.info("** Finished conversion for publication: %s", cls.config.publication_number)
        return result
