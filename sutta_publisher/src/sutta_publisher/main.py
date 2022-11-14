import logging
import os
from typing import Type

import click
from edition_parsers.base import EditionParser
from shared.config import get_edition_configs, setup_logging
from shared.data import get_edition_data
from shared.github_handler import update_run_sha
from shared.publisher import publish
from shared.value_objects.edition import EditionType
from shared.value_objects.edition_config import EditionsConfigs

logging.basicConfig(encoding="utf-8", level=logging.getLevelName(os.environ.get("PYTHONLOGLEVEL", "INFO")))
log = logging.getLogger(__name__)


def run(editions: EditionsConfigs, api_key: str, is_manual: bool) -> None:
    """Run the script engine. Configuration should be already done via the setup functions."""
    edition_list = []
    edition_class_mapping: dict[EditionType, Type[EditionParser]] = {}
    EditionParser.get_edition_mapping(edition_class_mapping)
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
        # if edition.edition_type in ("html"):  # dev
        if edition.edition_type in ("html", "epub", "paperback"):
            log.info(
                f"Generating {edition.config.publication.translation_title}... [{edition.config.edition.publication_type}]"
            )

            try:
                _edition_result = edition.collect_all()
                publish(result=_edition_result, api_key=api_key)
            except Exception as e:
                log.exception(e)

    if not is_manual and not os.getenv("PYTHONDEBUG", ""):
        update_run_sha(api_key)

    log.debug("*** Script finished ***")


@click.command()
@click.argument("api_key", default=None)
@click.argument("publication_numbers", default=None, required=False)
def setup_and_run(api_key: str, publication_numbers: str) -> None:
    """Setup and run the engine. It's entrypoint of the script."""

    try:
        setup_logging()
        editions = get_edition_configs(api_key=api_key, publication_numbers=publication_numbers)
        run(editions=editions, api_key=api_key, is_manual=bool(publication_numbers))
    except Exception as e:
        log.exception(e)
        raise
