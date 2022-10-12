import json
import logging
import re
from base64 import b64encode
from pathlib import Path
from typing import cast

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

    request = requests.put(f"{repo_url}{file_path.name}", data=json.dumps(body), headers=headers)
    request.raise_for_status()


def __get_request_headers(api_key: str) -> dict[str, str]:
    """Creates request headers for GitHub API."""

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {api_key}"
    }


def __get_request_body(file_path: Path, repo_url: str) -> dict[str, str]:
    """Creates request body for GitHub API.

    Parameters:
        file_path: path of the file to be uploaded
        repo_url: url of SuttaCentral editions repo
    """

    return {
        "message": f"Uploading {file_path.name}",
        "content": b64encode(file_path.read_bytes()).decode("ascii"),
        "sha": __get_file_sha(file_path.name, repo_url),
    }


def __get_file_sha(filename: str, repo_url: str) -> str:
    """Return sha for existing file. If file does not exist returns empty string.

    Parameters:
        filename: name of the file to be uploaded
        repo_url: url of SuttaCentral editions repo
    """

    response = requests.get(repo_url, headers={"Accept": "application/vnd.github+json"})

    if response.status_code == 200:
        pattern = r"([A-Za-z-]+-)(?:\d+-\d+-+\d+)(-\d+)?(.zip)"
        _source_match = re.search(pattern, filename)

        for _file in response.json():
            _target_match = re.search(pattern, _file.get("name"))
            if _source_match and _target_match and _target_match.groups() == _source_match.groups():
                return cast(str, _file.get("sha", ""))

    return ""
