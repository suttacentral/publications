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
    api_key: str = _get_api_key()
    repo_url: str = _get_repo_url_pattern().format(**result.dict())
    temp_dir = Path(tempfile.gettempdir())

    for volume in result.volumes:
        filename = volume[0].stem.strip("-cover")
        zip_path = (temp_dir / filename).with_suffix(".zip")

        with ZipFile(zip_path, "w") as zip_file:
            for _path in volume:
                zip_file.write(filename=_path, arcname=_path.name)

        log.info(f"Publishing results: {', '.join(_path.name for _path in volume)}.")

        upload_file_to_repo(zip_path, repo_url, api_key)

    log.info("** Publication uploaded to repo **")
