import logging
import os

from sutta_publisher.shared.github_handler import upload_files_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def _get_repo_url() -> str:
    repo_url = os.getenv("REPO_URL")
    if not repo_url:
        raise EnvironmentError(
            "Missing .env_public file or the file lacks variable REPO_URL. Example:\n"
            'REPO_URL = "https://api.github.com/repos/suttacentral/editions"'
        )
    return repo_url


def _get_repo_path_pattern() -> str:
    repo_path_pattern = os.getenv("REPO_PATH_PATTERN")
    if not repo_path_pattern:
        raise EnvironmentError(
            "Missing .env_public file or the file lacks variable REPO_PATH_PATTERN. Example:\n"
            'REPO_PATH_PATTERN = "{translation_lang_iso}/{creator_uid}/{text_uid}/{publication_type}"'
        )
    return repo_path_pattern


def publish(result: EditionResult, api_key: str) -> None:
    repo_url: str = _get_repo_url()
    repo_path: str = _get_repo_path_pattern().format(**result.dict())

    for volume in result.volumes:
        log.info(f"Publishing results: {', '.join(_path.name for _path in volume)}.")

        upload_files_to_repo(result, volume, repo_url, repo_path, api_key)

    log.info("** Publication uploaded to repo **")
