import logging
import os
from typing import Type

import click
from edition_parsers.base import EditionParser
from shared.config import get_editions_configs, setup_logging
from shared.data import get_edition_data
from shared.publisher import publish
from shared.value_objects.edition_config import EditionsConfigs

logging.basicConfig(encoding="utf-8", level=logging.getLevelName(os.environ.get("PYTHONLOGLEVEL", "INFO")))
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
        # if edition.edition_type in ("html", "epub", "pdf"):
        if edition.edition_type in ("html", "epub"):
            log.debug(edition)

            try:
                file_like_obj = edition.collect_all()
                publish(file_like_obj)
            except Exception as e:
                log.exception(e)

    log.debug("*** Script finished ***")


@click.command()
@click.argument("publication_number_list", default="noop_number")
@click.argument("token", default=None)
def setup_and_run(publication_number_list: str, token: str) -> None:
    """Setup and run the engine. It's entrypoint of the script."""

    try:
        setup_logging()
        editions = get_editions_configs(publication_number=publication_number_list)
        run(editions=editions)
    except Exception as e:
        log.exception(e)
        raise
