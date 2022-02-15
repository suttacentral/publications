import logging
from pathlib import Path

from sutta_publisher.shared.value_objects.results import IngestResult

from .base import Publisher

log = logging.getLogger(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="rn">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Test</title>
</head>
<body>
{}
</body>
</html>
"""


class HtmlPublisher(Publisher):
    @classmethod
    def publish(cls, result: IngestResult) -> None:
        output_path = Path.cwd() / "output.html"
        log.info("** Publishing results in a file: %s", output_path)
        with open(output_path, "w") as f:
            f.write(HTML_TEMPLATE.format(result.content))
        log.info("** Finished publishing results")
