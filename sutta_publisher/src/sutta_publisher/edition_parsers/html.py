import logging
import os

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser

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

        # _volumes_in_html = [BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_html()]  # type: ignore
        # frontmatters = [
        #     BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_frontmatter().values()
        # ]  # type: ignore # TODO: resolve this
        #
        # volume_number = 0
        # for _config, _html in zip(self.config.edition.volumes, _volumes_in_html):
        #     volume_number = +1
        #     book = epub.EpubBook()
        #     book.spine = [
        #         "nav",
        #     ]
        #
        #     self.__set_metadata(book)
        #     self.__set_styles(book)
        #
        #     for _frontmatter in frontmatters:
        #         self.__set_chapters(book, html=_frontmatter, chapter_number=volume_number, make_index=False)
        #         volume_number = +1
        #
        #     self.__set_chapters(book, html=_html, chapter_number=volume_number)
        #
        #     # add navigation files
        #     book.add_item(epub.EpubNcx())
        #     book.add_item(epub.EpubNav())
        #
        #     _path = os.path.join(
        #         tempfile.gettempdir(), f"{self.config.publication.translation_title} vol {volume_number}.epub"
        #     )
        #     # create epub file
        #     epub.write_epub(_path, book, {})

    def collect_all(self) -> EditionResult:
        # self.__generate_endmatter()
        self.__generate_html()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
