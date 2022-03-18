import logging
import os

from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

log = logging.getLogger(__name__)


class HtmlEdition(EditionParser):
    edition_type = EditionType.html

    def __get_standalone_html_css(self) -> str:
        """Returns css stylesheet as a string"""

        with open(os.path.dirname(__file__) + "/css_stylesheets/standalone_html.css", "r") as css_file:
            content = css_file.read()

        return content

    def __generate_html(self) -> None:
        log.debug("Generating html...")

    def collect_all(self) -> EditionResult:
        # self.__generate_backmatter()
        self.__generate_html()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
