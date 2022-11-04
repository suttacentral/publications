import json
import logging
import re
import tempfile
from base64 import b64encode
from pathlib import Path
from time import sleep

import requests
from requests import Response

from sutta_publisher.shared import EDITIONS_REPO_URL, LAST_RUN_SHA_FILE_URL
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)

MAX_GITHUB_REQUEST_ERRORS = 3


def worker(queue: list[dict], api_key: str = None, silent: bool = False) -> list[Response]:

    _queue: list[tuple[int, dict]] = [(_i, _t) for _i, _t in enumerate(queue)]
    errors = 0
    finished: list[tuple[int, Response]] = []

    while _queue and errors < MAX_GITHUB_REQUEST_ERRORS:
        _id, _task = _queue.pop(0)

        if not (_method := _task.get("method")):
            raise SystemExit("Requests worker error: Request method not provided.")
        if not (_headers := _task.get("headers")):
            _headers = {"Accept": "application/vnd.github+json"}
        if api_key:
            _headers["Authorization"] = f"Token {api_key}"

        _response: Response = getattr(requests, _method)(
            url=_task.get("url"),
            headers=_headers,
            data=_task.get("body"),
        )

        try:
            _response.raise_for_status()
        except requests.HTTPError:
            errors += 1
            _queue.append((_id, _task))
            log.error(_response.json().get("message"))
            sleep(1)
        else:
            errors = 0
            finished.append((_id, _response))

    if errors and not silent:
        raise SystemExit(f"Error while executing HTTP requests: {_queue[0][1].get('help_text')}")

    return [_res for _, _res in sorted(finished)] if finished else []


def get_last_commit_sha(repo_url: str, branch: str) -> str:
    """Get SHA of the last commit"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/branches/{branch}",
        "help_text": "get last commit sha",
    }
    _response: Response = worker(queue=[_request])[0]

    sha: str = _response.json()["commit"]["sha"]
    return sha


def get_blob_shas(file_paths: list[Path], repo_url: str, api_key: str) -> list[str]:
    """Upload blobs of new files and return list of their SHAs"""
    _requests: list[dict] = [
        {
            "method": "post",
            "url": f"{repo_url}/git/blobs",
            "body": json.dumps({"content": b64encode(_file.read_bytes()).decode("ascii"), "encoding": "base64"}),
            "help_text": "get blob shas",
        }
        for _file in file_paths
    ]
    _responses: list[Response] = worker(queue=_requests, api_key=api_key)

    shas: list[str] = [_response.json()["sha"] for _response in _responses]
    return shas


def match_file(filename: str, content: list[dict]) -> dict:
    """Return a dict with matching file details. Return empty dict if file not found."""

    _PATTERN = r"([A-Za-z-]+-)(?:\d+-\d+-+\d+)(-\d+)?(-cover)?(.[a-z]+)"
    _new_file_match = re.search(_PATTERN, filename)

    for _file in content:
        _old_file_match = re.search(_PATTERN, _file.get("name", ""))
        if _new_file_match and _old_file_match and _new_file_match.groups() == _old_file_match.groups():
            return _file

    return {}


def get_old_files_shas(file_paths: list[Path], repo_url: str, repo_path: str) -> list[str]:
    """Get SHAs of current files to be updated in repo"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/contents/{repo_path}",
        "help_text": "get old files shas",
    }
    _responses: list[Response] = worker(queue=[_request], silent=True)

    if not _responses:
        return []

    old_files_shas: list[str] = []
    _content = _responses[0].json()

    for file in file_paths:
        remote_file = match_file(file.name, _content)
        if remote_file:
            old_files_shas.append(remote_file["sha"])

    return old_files_shas


def create_new_tree(
    file_paths: list[Path],
    repo_url: str,
    repo_path: str,
    last_commit_sha: str,
    blob_shas: list[str],
    old_files_shas: list[str],
) -> list[dict]:
    """Create new Git tree with updated files"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/git/trees/{last_commit_sha}?recursive=1",
        "help_text": "create new tree",
    }
    _responses: list[Response] = worker(queue=[_request], silent=True)

    _old_tree = _responses[0].json().get("tree", []) if _responses else []

    new_tree: list[dict] = [
        _item for _item in _old_tree if _item.get("type") == "blob" and not _item.get("sha") in old_files_shas
    ]
    new_tree.extend(
        [
            {
                "path": f"{repo_path}{'/' if repo_path else ''}{_file.name}",
                "mode": "100644",
                "type": "blob",
                "sha": _sha,
            }
            for _file, _sha in zip(file_paths, blob_shas)
        ]
    )
    return new_tree


def get_tree_sha(repo_url: str, api_key: str, tree: list[dict]) -> str:
    """Post a new tree and return its SHA"""
    _request = {
        "method": "post",
        "url": f"{repo_url}/git/trees",
        "body": json.dumps({"tree": tree}),
        "help_text": "create new tree",
    }
    _response: Response = worker(queue=[_request], api_key=api_key)[0]

    sha: str = _response.json()["sha"]
    return sha


def get_new_commit_sha(
    edition: EditionResult, file_paths: list[Path], repo_url: str, api_key: str, last_commit_sha: str, tree_sha: str
) -> str:
    """Return SHA of new commit"""
    _message = (
        f"Update {edition.translation_title} ({edition.publication_type})"
        if edition
        else f"Update {', '.join(_file.name for _file in file_paths)}"
    )

    _request = {
        "method": "post",
        "url": f"{repo_url}/git/commits",
        "body": json.dumps(
            {
                "message": _message,
                "parents": [last_commit_sha],
                "tree": tree_sha,
            }
        ),
        "help_text": "create new commit",
    }
    _response: Response = worker(queue=[_request], api_key=api_key)[0]

    sha: str = _response.json()["sha"]
    return sha


def update_head(repo_url: str, api_key: str, new_commit_sha: str) -> None:
    """Update HEAD ref"""
    _request = {
        "method": "post",
        "url": f"{repo_url}/git/refs/heads/main",
        "body": json.dumps({"sha": new_commit_sha}),
        "help_text": "update HEAD ref",
    }
    worker(queue=[_request], api_key=api_key)


def upload_files_to_repo(
    file_paths: list[Path], repo_url: str, repo_path: str, api_key: str, edition: EditionResult = None
) -> None:

    last_commit_sha: str = get_last_commit_sha(repo_url, "main")

    blob_shas: list[str] = get_blob_shas(file_paths, repo_url, api_key)

    old_files_shas: list[str] = get_old_files_shas(file_paths, repo_url, repo_path)

    new_tree: list[dict] = create_new_tree(file_paths, repo_url, repo_path, last_commit_sha, blob_shas, old_files_shas)

    tree_sha: str = get_tree_sha(repo_url, api_key, new_tree)

    new_commit_sha: str = get_new_commit_sha(edition, file_paths, repo_url, api_key, last_commit_sha, tree_sha)

    update_head(repo_url, api_key, new_commit_sha)


def get_modified_filenames(repo_url: str, last_run_sha: str, last_commit_sha: str) -> list[str]:
    _request = {
        "method": "get",
        "url": f"{repo_url}/compare/{last_run_sha}...{last_commit_sha}",
        "help_text": "get modified filenames",
        "headers": {"Accept": "application/vnd.github.v3.diff"},
    }
    _response: Response = worker(queue=[_request])[0]

    _diff: str = _response.content.decode()

    filenames: list[str] = []
    for _line in _diff.split("\n"):
        if _line.startswith("diff") and "/sc_bilara_data/" in _line:
            filenames.append(_line)

    return filenames


def update_run_sha(api_key: str) -> None:
    last_sha_filename: str = LAST_RUN_SHA_FILE_URL.split("/")[-1]
    last_commit_sha = get_last_commit_sha(repo_url=EDITIONS_REPO_URL, branch="main")

    _path = Path(tempfile.gettempdir()) / last_sha_filename
    with open(file=_path, mode="wt") as f:
        f.write(last_commit_sha)

    upload_files_to_repo(
        file_paths=[_path],
        repo_url=EDITIONS_REPO_URL,
        repo_path="",
        api_key=api_key,
    )
