import logging
import os
import tempfile
from pathlib import Path
from zipfile import ZipFile

from sutta_publisher.shared.github_handler import upload_file_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def _get_repo_url_pattern() -> str:
    repo_url_pattern = os.getenv("GITHUB_UPLOAD_URL")
    if not repo_url_pattern:
        raise EnvironmentError(
            "Missing .env_public file or the file lacks variable GITHUB_UPLOAD_URL. Example:\n"
            'GITHUB_UPLOAD_URL = "https://api.github.com/repos/suttacentral/editions/contents/{file_path}"'
        )
    return repo_url_pattern


def _get_api_key() -> str:
    api_key = os.getenv("BOT_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing repository secret environmental variable BOT_API_KEY.")
    return api_key


def publish(result: EditionResult) -> None:
    log.info("Publishing results: %s", ", ".join(map(str, result.file_paths)))
    api_key: str = _get_api_key()
    repo_url_pattern: str = _get_repo_url_pattern()

    temp_dir = Path(tempfile.gettempdir())
    filename = result.file_paths[0].stem.strip("-cover")
    zip_path = (temp_dir / filename).with_suffix(".zip")

    repo_url = repo_url_pattern.format(filename=zip_path.name, **result.dict())

    with ZipFile(zip_path, "w") as zip_file:
        for _file_path in result.file_paths:
            zip_file.write(filename=_file_path, arcname=_file_path.name)

    upload_file_to_repo(zip_path, repo_url, api_key)
