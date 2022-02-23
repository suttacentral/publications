import json
import logging
from base64 import b64encode
from io import BytesIO

import requests

log = logging.getLogger(__name__)


def upload_file_to_repo(file_path: str, file: BytesIO, repo_url: str, api_key: str) -> None:
    """Uploads given file to SuttaCentral's editions repository.
    Parameters:
        file_path (string): path where file is to be uploaded (e.g. /folder1/folder2/file.html)
        file (BytesIO): File-like object
        repo_url (string): url of SuttaCentral editions repo
        api_key (string): personal token of bot gh account
    """
    headers = __get_request_headers(api_key)
    body = __get_request_body(file, file_path, repo_url)

    request = requests.put(repo_url.format(file_name=file_path), data=json.dumps(body), headers=headers)
    request.raise_for_status()

    log.info("** Publication uploaded to repo")


def __get_request_headers(api_key: str) -> dict:
    """Creates request headers for GitHub API."""

    return {"Authorization": f"token {api_key}"}


def __get_request_body(file: BytesIO, file_path: str, repo_url: str) -> dict:
    """Creates request body for GitHub API.
    Parameters:
        file_path (string): path where file is to be uploaded (e.g. /folder1/folder2/file.html)
        file (BytesIO): File-like object
        repo_url (string): url of SuttaCentral editions repo
    """

    return {
        "message": f"Uploading {file_path}",
        "content": b64encode(file.read()).decode("ascii"),
        "sha": __get_file_sha(file_path, repo_url),
    }


def __get_file_sha(file_path: str, repo_url: str) -> str:
    """Return sha for existing file. If file does not exist returns empty string.
    Parameters:
        file_path (string): path where file is to be uploaded (e.g. /folder1/folder2/file.html)
        repo_url (string): url of SuttaCentral editions repo
    """
    response = requests.get(repo_url.format(file_name=file_path))

    sha_val = response.json().get("sha") or ""

    return sha_val
