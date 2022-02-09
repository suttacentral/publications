import logging

import click
import inject

from sutta_publisher.ingester.base import Ingester
from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.shared.config import setup_inject, setup_logging

log = logging.getLogger(__name__)


def run() -> None:
    """Run the script engine. Configuration should be already done via the setup functions."""
    ingest_result = Ingester.get_result()
    publishers_list = inject.instance(ActivePublishers)
    for publisher in publishers_list:
        publisher.publish(result=ingest_result)
    log.info("*** Script finished ***")


@click.command()
@click.argument("publication_number", default="noop_number")
def setup_and_run(publication_number: str) -> None:
    """Setup and run the engine. It's entrypoint of the script."""
    try:
        setup_logging()
        setup_inject(publication_number=publication_number)
        run()
    except Exception as e:
        log.exception(e)
        raise
