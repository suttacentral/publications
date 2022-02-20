import logging
from typing import Type

import click

from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.config import get_editions_configs, setup_logging
from sutta_publisher.shared.data import get_edition_data
from sutta_publisher.shared.publisher import publish
from sutta_publisher.shared.value_objects.edition_config import EditionsConfigs

log = logging.getLogger(__name__)


def run(editions: EditionsConfigs) -> None:
    """Run the script engine. Configuration should be already done via the setup functions."""
    edition_list = []
    edition_class_mapping = EditionParser.get_edition_mapping()
    for edition_config in editions:
        try:
            edition_klass: Type[EditionParser] = edition_class_mapping[edition_config.edition.publication_type]
            edition_data = get_edition_data(edition_config=edition_config)
            edition_list.append(edition_klass(config=edition_config, data=edition_data))
        except KeyError:
            log.warning("No module to parse publication_type=%s", edition_config.edition.publication_type)
        except Exception as e:
            log.exception("Can't parse publication_type='%s'. Error: %s", edition_config.edition.publication_type, e)

    for edition in edition_list:  # type: EditionParser
        try:
            file_like_obj = edition.collect_all()
            publish(file_like_obj)
        except Exception as e:
            log.exception(e)

    log.info("*** Script finished ***")


@click.command()
@click.argument("publication_number", default="noop_number")
def setup_and_run(publication_number: str) -> None:
    """Setup and run the engine. It's entrypoint of the script."""
    try:
        setup_logging()
        editions = get_editions_configs(publication_number=publication_number)
        run(editions=editions)
    except Exception as e:
        log.exception(e)
        raise