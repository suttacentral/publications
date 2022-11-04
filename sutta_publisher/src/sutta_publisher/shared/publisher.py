import logging
import os

from sutta_publisher.shared import EDITIONS_REPO_URL, REPO_PATTERN
from sutta_publisher.shared.github_handler import upload_files_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def publish(result: EditionResult, api_key: str) -> None:
    for volume in result.volumes:
        log.info(
            f"** Publishing {result.translation_title} ({result.publication_type}) **\n"
            f"Files: {', '.join(_path.name for _path in volume)}."
        )

        if not os.getenv("PYTHONDEBUG", ""):
            upload_files_to_repo(
                edition=result,
                file_paths=volume,
                repo_url=EDITIONS_REPO_URL,
                repo_path=REPO_PATTERN.format(**result.dict()),
                api_key=api_key,
            )

    log.info("** Publication uploaded to repo **")
