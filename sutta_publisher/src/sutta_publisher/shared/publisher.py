import logging
import os

from sutta_publisher.shared import get_from_env
from sutta_publisher.shared.github_handler import upload_files_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


REPO_URL: str = get_from_env(
    name="EDITIONS_REPO_URL", example='EDITIONS_REPO_URL = "https://api.github.com/repos/suttacentral/editions"'
)
REPO_PATTERN: str = get_from_env(
    name="REPO_PATH_PATTERN",
    example='REPO_PATH_PATTERN = "{translation_lang_iso}/{creator_uid}/{text_uid}/{publication_type}"',
)


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
                repo_url=REPO_URL,
                repo_path=REPO_PATTERN.format(**result.dict()),
                api_key=api_key,
            )

    log.info("** Publication uploaded to repo **")
