import logging
import tempfile
from subprocess import PIPE, Popen  # nosec

from sutta_publisher.shared.value_objects.edition import EditionType

from .base import EditionParser

log = logging.getLogger(__name__)


class EpubEdition(EditionParser):
    edition_type = EditionType.epub

    def __generate_epub(self) -> str:
        """Generate epub"""
        log.info("Generating epub...")
        _html = self._EditionParser__generate_html()  # type: ignore
        _, _tmpfile = tempfile.mkstemp(prefix="raw_", suffix=".html")

        with open(_tmpfile, "w") as _file:
            _file.write(_html)

            epub = f"{_tmpfile}.epub"
            pandoc = "pandoc"

        cmd = f"{pandoc} {_tmpfile} -f html -t epub3 -o {epub}"

        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)  # nosec
        stdout, stderr = p.communicate()
        return epub
