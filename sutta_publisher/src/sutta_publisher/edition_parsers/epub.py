import logging
import os
import tempfile
from typing import List, Tuple, Union

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

    def __set_metadata(self, book: epub.EpubBook) -> None:
        book.set_identifier(self.config.edition.edition_id)
        book.set_title(self.config.publication.translation_title)
        book.set_language(self.config.publication.translation_lang_iso)
        book.add_author(self.config.publication.creator_name)

    def __set_styles(self, book: epub.EpubBook) -> None:
        default_css = epub.EpubItem(
            uid="style_default", file_name="style/default.css", media_type="text/css", content=_css
        )
        book.add_item(default_css)

    def __make_chapter_content(self, html: BeautifulSoup, file_name: str) -> epub.EpubHtml:
        _chapter = epub.EpubHtml(title=self.config.publication.translation_title, file_name=file_name)
        _chapter.content = str(html)
        return _chapter

    def __make_chapter_index(
        self, html: BeautifulSoup, file_name: str, section_name: str = ""
    ) -> Union[List[Tuple[epub.Section, List[epub.Link]]], List[epub.Link]]:
        _links = [epub.Link(f"{file_name}#{l.span['id']}", l.text, l.span["id"]) for l in html.find_all("h1")]
        if section_name:
            return [
                (epub.Section(section_name), _links),
            ]
        else:
            return _links

    def __make_chapter(
        self, html: BeautifulSoup, chapter_number: int, section_name: str = ""
    ) -> Tuple[epub.EpubHtml, List[epub.Link]]:
        file_name = f"chapter_{chapter_number}.xhtml"
        chapter = self.__make_chapter_content(html, file_name)
        index = _chapter = self.__make_chapter_index(html, file_name, section_name=section_name)
        return chapter, index

    def __set_chapters(
        self, book: epub.EpubBook, html: BeautifulSoup, chapter_number: int, section_name: str = ""
    ) -> None:
        chapter, index = self.__make_chapter(html=html, chapter_number=chapter_number, section_name=section_name)
        book.add_item(chapter)
        book.toc.extend(index)
        book.spine.append(chapter)

    def __generate_epub(self) -> None:
        """Generate epub"""
        log.debug("Generating epub...")

        _volumes_in_html = [BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_html()]  # type: ignore

        volume_number = 0
        for _config, _html in zip(self.config.edition.volumes, _volumes_in_html):
            volume_number = +1
            book = epub.EpubBook()
            book.spine = [
                "nav",
            ]

            self.__set_metadata(book)
            self.__set_styles(book)
            self.__set_chapters(book, html=_html, chapter_number=volume_number)

            # add navigation files
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())

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
