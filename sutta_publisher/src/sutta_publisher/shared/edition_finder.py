from requests import Response

from sutta_publisher.shared import EDITION_FINDER_PATTERNS, LAST_RUN_DATE_FILE_URL, SCDATA_REPO_URL, SUPER_TREE_URL
from sutta_publisher.shared.github_handler import get_last_commit_sha, get_modified_filenames, worker


def get_last_run_date() -> str:
    """Get the last run date. ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ"""
    _request = {
        "method": "get",
        "url": LAST_RUN_DATE_FILE_URL,
        "help_text": "get last run date",
    }
    _response: Response = worker(queue=[_request])[0]

    last_run_sha: str = _response.content.decode("ascii").strip()
    return last_run_sha


def get_last_run_sha(repo: str, api_key: str, date: str) -> str:
    _request = {
        "method": "get",
        "url": f"{repo}/commits?until={date}",
        "help_text": f"get list of commits until {date}",
    }
    _response: Response = worker(queue=[_request], api_key=api_key)[0]

    last_run_sha: str = _response.json()[0]["sha"]
    return last_run_sha


def get_super_tree() -> list[dict]:
    _request = {
        "method": "get",
        "url": SUPER_TREE_URL,
        "help_text": "get super tree",
    }
    _response: Response = worker(queue=[_request])[0]

    super_tree: list[dict] = _response.json()
    return super_tree


def get_all_uids(tree: list[dict | str], text_uid: str) -> list[str] | None:
    """Get all uids from super tree for a given publication"""
    for item in tree:
        if isinstance(item, str) and item == text_uid:
            return [text_uid]
        elif isinstance(item, dict):
            if list(item.keys())[0] == text_uid:
                uids: list[str] = [text_uid] + item[text_uid]
                return uids
            elif _item := get_all_uids(tree=list(item.values())[0], text_uid=text_uid):
                return _item

    return None


def get_mapping(data: list[dict[str, str]]) -> set[tuple[str, str, str, tuple[str, ...]]]:
    mapping = set()

    super_tree: list[dict] = get_super_tree()

    for _entry in data:
        _publication_number = _entry["publication_number"]

        _temp = _entry["edition_id"].split("_")[0].split("-")
        _text_uid, _lang_iso, _creator = "-".join(_temp[:-2]), _temp[-2], _temp[-1]

        _uids = get_all_uids(tree=super_tree, text_uid=_text_uid)  # type: ignore
        if not _uids:
            raise SystemExit("Could not find matching uids in a super tree.")
        _uids_tuple = tuple(_uid for _uid in _uids)

        _mapping_item = (_publication_number, _lang_iso, _creator, _uids_tuple)
        mapping.add(_mapping_item)

    return mapping


def _match_all(patterns: tuple[str, ...] | None, filename: str, lang_iso: str, creator: str, uid: str) -> bool:
    return not patterns or all(
        [_pattern.format(lang_iso=lang_iso, creator=creator, uid=uid) in filename for _pattern in patterns]
    )


def _match_any(patterns: tuple[str, ...] | None, filename: str, lang_iso: str, creator: str, uid: str) -> bool:
    return not patterns or any(
        [_pattern.format(lang_iso=lang_iso, creator=creator, uid=uid) in filename for _pattern in patterns]
    )


def _get_match(publication: tuple[str, str, str, tuple[str, ...]], filenames: list[str], patterns: list[dict]) -> bool:
    lang_iso = publication[1]
    creator = publication[2]
    uids = publication[3]

    for uid in uids:

        for _pattern in patterns:

            all_ = _pattern.get("all")
            any_ = _pattern.get("any")

            for filename in filenames:

                if _match_all(all_, filename, lang_iso, creator, uid) and _match_any(
                    any_, filename, lang_iso, creator, uid
                ):
                    return True
    return False


def match_filenames_to_publication_numbers(
    filenames: list[str], mapping: set[tuple[str, str, str, tuple[str, ...]]]
) -> list[str]:
    publication_numbers = []

    for _publication in mapping:
        _publication_number = _publication[0]
        _match = _get_match(publication=_publication, filenames=filenames, patterns=EDITION_FINDER_PATTERNS)

        if _match:
            publication_numbers.append(_publication_number)

    return publication_numbers


def find_edition_ids(data: list[dict[str, str]], api_key: str) -> list[str]:
    """
    Look for files that were modified since the last run of publications app and match them with edition ids.
    """
    last_run_date: str = get_last_run_date()

    last_run_sha: str = get_last_run_sha(repo=SCDATA_REPO_URL, api_key=api_key, date=last_run_date)

    last_commit_sha: str = get_last_commit_sha(repo_url=SCDATA_REPO_URL, api_key=api_key, branch="main")

    filenames: list[str] = get_modified_filenames(
        repo_url=SCDATA_REPO_URL, api_key=api_key, last_run_sha=last_run_sha, last_commit_sha=last_commit_sha
    )

    mapping = get_mapping(data=data)

    publication_numbers = match_filenames_to_publication_numbers(filenames=filenames, mapping=mapping)

    edition_ids = [edition["edition_id"] for edition in data if edition["publication_number"] in publication_numbers]

    return edition_ids
