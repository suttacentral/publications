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
        # log.info("** Running conversion for publication: %s", cls.config.publication_number)
        parser = TsvParser("dn.tsv")
        # result = IngestResult(content=f"<html><body>{cls.config.publication_number=}</body></html>")
        result = IngestResult(content=f"<html><body>{parser.parse_input()}</body></html>")
        # log.info("** Finished conversion for publication: %s", cls.config.publication_number)
        print(parser.parse_input())
        return result
