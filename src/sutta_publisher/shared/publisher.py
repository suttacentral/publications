import logging
from io import StringIO

from sutta_publisher.shared.github_handler import upload_file_to_repo
from sutta_publisher.shared.value_objects.edition import EditionResult

log = logging.getLogger(__name__)


def publish(result: EditionResult, token: str) -> None:
    log.info("Publishing results: %s")
    result.seek(0)
    
    print("-----------------------------------------------")
    string = EditionResult.read()[::1]    
    print(string)
    print("-----------------------------------------------")
    
    """
        upload_file_to_repo(
            "example.html", EditionResult, "https://api.github.com/repos/suttacentral/contents/{file_name}", token
        )
    """