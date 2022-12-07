import logging
import os
from pathlib import Path

from sutta_publisher.edition_parsers.helper_functions import make_paperback_zip_files
from sutta_publisher.shared import EDITIONS_REPO_URL, REPO_PATTERN
from sutta_publisher.shared.github_handler import upload_files_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def publish(result: EditionResult, api_key: str) -> None:
    file_paths: list[Path] = [_path for _volume in result.volumes for _path in _volume]

    if result.publication_type == "paperback":
        _zip_paths = make_paperback_zip_files(paths=file_paths, num_of_volumes=len(result.volumes))
        file_paths = _zip_paths

    volumes_info = f"({len(result.volumes)} volumes) " if len(result.volumes) > 1 else ""
    log.info(
        f"Publishing {result.translation_title}... {volumes_info}[{result.publication_type}]\n"
        f"Files: {', '.join(_path.name for _path in file_paths)}"
    )

    if not os.getenv("PYTHONDEBUG", ""):
        upload_files_to_repo(
            edition=result,
            file_paths=file_paths,
            repo_url=EDITIONS_REPO_URL,
            repo_path=REPO_PATTERN.format(**result.dict()),
            api_key=api_key,
        )

    log.info("** Publication uploaded successfully! **")
