import json
import logging
from base64 import b64encode
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def upload_file_to_repo(file_path: Path, repo_url: str, api_key: str) -> None:
    """Uploads given file to `SuttaCentral`'s editions repository.

    Parameters:
        file_path: path of the file to be uploaded
        repo_url: url of SuttaCentral editions repo
        api_key: personal token of bot gh account
    """
    headers = __get_request_headers(api_key)
    body = __get_request_body(file_path, repo_url)

    request = requests.put(repo_url, data=json.dumps(body), headers=headers)
    request.raise_for_status()

    log.info("** Publication uploaded to repo")


def __get_request_headers(api_key: str) -> dict[str, str]:
    """Creates request headers for GitHub API."""

    return {"Authorization": f"token {api_key}"}


def __get_request_body(file_path: Path, repo_url: str) -> dict[str, str]:
    """Creates request body for GitHub API.

    Parameters:
        file_path: path of the file to be uploaded
        repo_url: url of SuttaCentral editions repo
    """

    return {
        "message": f"Uploading {file_path.name}",
        "content": b64encode(file_path.read_bytes()).decode("ascii"),
        "sha": __get_file_sha(repo_url),
    }


def __get_file_sha(repo_url: str) -> str:
    """Return sha for existing file. If file does not exist returns empty string.

    Parameters:
        repo_url: url of SuttaCentral editions repo
    """

    response = requests.get(repo_url)
    sha_val = response.json().get("sha") or ""

    return sha_val
