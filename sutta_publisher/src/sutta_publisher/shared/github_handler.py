import json
import logging
import re
from base64 import b64encode
from pathlib import Path
from time import sleep

import requests
from requests import Response

from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)

MAX_GITHUB_REQUEST_ERRORS = 3


def worker(queue: dict | list[dict], api_key: str, silent: bool = False) -> list[Response]:
    if isinstance(queue, dict):
        queue = [queue]

    _queue: list[tuple[int, dict]] = [(_i, _t) for _i, _t in enumerate(queue)]
    _errors = 0
    _finished: list[tuple[int, Response]] = []

    while _queue and _errors < MAX_GITHUB_REQUEST_ERRORS:
        _id, _task = _queue.pop(0)
        try:
            _response: Response = getattr(requests, _task["method"])(
                url=_task.get("url"),
                headers={"Accept": "application/vnd.github+json", "Authorization": f"Token {api_key}"},
                data=_task.get("body"),
            )
            _response.raise_for_status()
        except requests.HTTPError:
            _errors += 1
            _queue.append((_id, _task))
            sleep(1)
        else:
            _errors = 0
            _finished.append((_id, _response))

    if _errors and not silent:
        raise SystemExit(f"Error while executing HTTP requests: {_queue[0][1].get('type')}")

    return [_res for _, _res in sorted(_finished)]


def _get_last_commit_sha(repo_url: str, api_key: str) -> str:
    """Get SHA of the last commit"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/branches/main",
        "type": "get last commit sha",
    }
    _responses = worker(_request, api_key)

    sha: str = _responses[0].json()["commit"]["sha"]
    return sha


def _get_blob_shas(file_paths: list[Path], repo_url: str, api_key: str) -> list[str]:
    """Upload blobs of new files and return list of their SHAs"""
    _requests: list[dict] = [
        {
            "method": "post",
            "url": f"{repo_url}/git/blobs",
            "body": json.dumps({"content": b64encode(_file.read_bytes()).decode("ascii"), "encoding": "base64"}),
            "type": "get blob shas",
        }
        for _file in file_paths
    ]
    _responses = worker(_requests, api_key)

    shas: list[str] = [_response.json()["sha"] for _response in _responses]
    return shas


def _match_file(filename: str, content: list[dict]) -> dict:
    """Return a dict with matching file details. Return empty dict if file not found."""

    _PATTERN = r"([A-Za-z-]+-)(?:\d+-\d+-+\d+)(-\d+)?(-cover)?(.[a-z]+)"
    _new_file_match = re.search(_PATTERN, filename)

    for _file in content:
        _old_file_match = re.search(_PATTERN, _file.get("name", ""))
        if _new_file_match and _old_file_match and _new_file_match.groups() == _old_file_match.groups():
            return _file

    return {}


def _get_old_files_shas(file_paths: list[Path], repo_url: str, repo_path: str, api_key: str) -> list[str]:
    """Get SHAs of current files to be updated in repo"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/contents/{repo_path}",
        "type": "get old files shas",
    }
    _responses = worker(_request, api_key, silent=True)

    if not _responses:
        return []

    old_files_shas: list[str] = []
    _content = _responses[0].json()

    for file in file_paths:
        remote_file = _match_file(file.name, _content)
        if remote_file:
            old_files_shas.append(remote_file["sha"])

    return old_files_shas


def _create_new_tree(
    file_paths: list[Path],
    repo_url: str,
    repo_path: str,
    api_key: str,
    last_commit_sha: str,
    blob_shas: list[str],
    old_files_shas: list[str],
) -> list[dict]:
    """Create new Git tree with updated files"""
    _request = {
        "method": "get",
        "url": f"{repo_url}/git/trees/{last_commit_sha}?recursive=1",
        "type": "create new tree",
    }
    _responses = worker(_request, api_key, silent=True)

    _old_tree = _responses[0].json().get("tree", []) if _responses else []

    new_tree: list[dict] = [
        _item for _item in _old_tree if _item.get("type") == "blob" and not _item.get("sha") in old_files_shas
    ]
    new_tree.extend(
        [
            {"path": f"{repo_path}/{_file.name}", "mode": "100644", "type": "blob", "sha": _sha}
            for _file, _sha in zip(file_paths, blob_shas)
        ]
    )
    return new_tree


def _get_tree_sha(repo_url: str, api_key: str, tree: list[dict]) -> str:
    """Post a new tree and return its SHA"""
    _request = {
        "method": "post",
        "url": f"{repo_url}/git/trees",
        "body": json.dumps({"tree": tree}),
        "type": "create new tree",
    }
    _responses = worker(_request, api_key)

    sha: str = _responses[0].json()["sha"]
    return sha


def _get_new_commit_sha(
    edition: EditionResult, repo_url: str, api_key: str, last_commit_sha: str, tree_sha: str
) -> str:
    """Return SHA of new commit"""
    _request = {
        "method": "post",
        "url": f"{repo_url}/git/commits",
        "body": json.dumps(
            {
                "message": f"Update {edition.translation_title} ({edition.publication_type})",
                "parents": [last_commit_sha],
                "tree": tree_sha,
            }
        ),
        "type": "create new commit",
    }
    _responses = worker(_request, api_key)

    sha: str = _responses[0].json()["sha"]
    return sha


def _update_head(repo_url: str, api_key: str, new_commit_sha: str) -> None:
    """Update HEAD ref"""
    _request = {
        "method": "post",
        "url": f"{repo_url}/git/refs/heads/main",
        "body": json.dumps({"ref": "refs/heads/main", "sha": new_commit_sha}),
        "type": "update HEAD ref",
    }
    worker(_request, api_key)


def upload_files_to_repo(
    edition: EditionResult, file_paths: list[Path], repo_url: str, repo_path: str, api_key: str
) -> None:

    last_commit_sha: str = _get_last_commit_sha(repo_url, api_key)

    blob_shas: list[str] = _get_blob_shas(file_paths, repo_url, api_key)

    old_files_shas: list[str] = _get_old_files_shas(file_paths, repo_url, repo_path, api_key)

    new_tree: list[dict] = _create_new_tree(
        file_paths, repo_url, repo_path, api_key, last_commit_sha, blob_shas, old_files_shas
    )

    tree_sha: str = _get_tree_sha(repo_url, api_key, new_tree)

    new_commit_sha: str = _get_new_commit_sha(edition, repo_url, api_key, last_commit_sha, tree_sha)

    _update_head(repo_url, api_key, new_commit_sha)
