"""
Objects from this package will be shared across modules, so there should not be imports
from other modules at the top of the file to avoid circular imports.
"""
import ast
import os


def get_from_env(name: str, example: str = "") -> str:
    env_var = os.getenv(name)
    if not env_var:
        _example = f" Example:\n{example}" if example else ""
        raise EnvironmentError(f"Missing .env_public file or the file lacks variable {name}.{_example}")
    return env_var


API_URL: str = get_from_env(name="API_URL", example='API_URL = "http://suttacentral.net/api/"')
API_ENDPOINTS: dict[str, str] = ast.literal_eval(
    get_from_env(
        name="API_ENDPOINTS",
        example="API_ENDPOINTS = '{"
        '"edition_mainmatter": "publication/edition/{edition_id}/{uid}",'
        '"edition_files": "publication/edition/{edition_id}/files",'
        '"editions_mapping": "publication/editions",'
        '"specific_edition": "publication/edition/{edition_id}",'
        "}'",
    )
)
CREATOR_BIOS_URL: str = get_from_env(
    name="CREATOR_BIOS_URL",
    example='CREATOR_BIOS_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/additional-info/creator_bio.json"',
)
EDITION_FINDER_PATTERNS: list[dict] = ast.literal_eval(
    get_from_env(
        name="EDITION_FINDER_PATTERNS",
        example="EDITION_FINDER_PATTERNS = '["
        '{"any": ("/_publication/", "/comment/"), "all": ("/{lang_iso}/", "/{creator}/", "/{uid}/")},'
        "]'",
    )
)
EDITIONS_REPO_URL: str = get_from_env(
    name="EDITIONS_REPO_URL", example='EDITIONS_REPO_URL = "https://api.github.com/repos/suttacentral/editions"'
)
LAST_RUN_DATE_FILE_URL: str = get_from_env(
    name="LAST_RUN_DATE_FILE_URL",
    example='LAST_RUN_DATE_FILE_URL = "https://raw.githubusercontent.com/suttacentral/editions/main/last_run_date"',
)
REPO_PATTERN: str = get_from_env(
    name="REPO_PATH_PATTERN",
    example='REPO_PATH_PATTERN = "{translation_lang_iso}/{creator_uid}/{text_uid}/{publication_type}"',
)
SCDATA_REPO_URL: str = get_from_env(
    name="SCDATA_REPO_URL", example='SCDATA_REPO_URL = "https://api.github.com/repos/suttacentral/sc-data"'
)
SUPER_TREE_URL: str = get_from_env(
    name="SUPER_TREE_URL",
    example='SUPER_TREE_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/structure/tree/super-tree.json"',
)
TREE_URL: str = get_from_env(
    name="TREE_URL",
    example='TREE_URL = "https://raw.githubusercontent.com/suttacentral/sc-data/master/structure/tree/{text_type}/{tree_uid}-tree.json"',
)
