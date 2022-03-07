import logging
import os
import tempfile
import uuid

from bs4 import BeautifulSoup
from ebooklib import epub

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser

log = logging.getLogger(__name__)


_css = """
@namespace epub "http://www.idpf.org/2007/ops";
body {
    font-family: Cambria, Liberation Serif, Bitstream Vera Serif, Georgia, Times, Times New Roman, serif;
}
h2 {
     text-align: left;
     text-transform: uppercase;
     font-weight: 200;
}
ol {
        list-style-type: none;
}
ol > li:first-child {
        margin-top: 0.3em;
}
nav[epub|type~='toc'] > ol > li > ol  {
    list-style-type:square;
}
nav[epub|type~='toc'] > ol > li > ol > li {
        margin-top: 0.3em;
}
"""


class EpubEdition(EditionParser):
    edition_type = EditionType.epub

    def __generate_epub(self) -> None:
        """Generate epub"""
        log.debug("Generating epub...")

        print(self.config.edition.volumes)
        volume_number = 0
        for _config, _html in zip(self.config.edition.volumes, self._EditionParser__generate_html()):  # type: ignore
            volume_number = +1

            file_name = f"content_{volume_number}.xhtml"

            book = epub.EpubBook()
            # add metadata
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(self.config.publication.translation_title)
            # book.set_language("en")
            book.add_author(self.config.publication.creator_name)

            default_css = epub.EpubItem(
                uid="style_default", file_name="style/default.css", media_type="text/css", content=_css
            )
            book.add_item(default_css)

            _chapter = epub.EpubHtml(title=self.config.publication.translation_title, file_name=file_name)
            _parsed_html = BeautifulSoup(_html, "lxml")
            _content_toc = []
            for l in _parsed_html.find_all("h1"):
                _content_toc.append(epub.Link(f"{file_name}#{l.span['id']}", l.text, l.span["id"]))
            _chapter.content = str(_parsed_html)
            book.add_item(_chapter)

            book.toc = (epub.Section("Content"), *_content_toc)

            # # add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

            # create spine
            book.spine = ["nav", _chapter]
            _path = os.path.join(
                tempfile.gettempdir(), f"{self.config.publication.translation_title} vol {volume_number}.epub"
            )
            # create epub file
            epub.write_epub(_path, book, {})

    def collect_all(self) -> EditionResult:
        # self.__generate_frontmatter()
        # self.__generate_endmatter()
        # self.__generate_covers()
        self.__generate_epub()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
