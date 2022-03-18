import logging
import os
import re
import tempfile
from typing import List, Tuple, Union

import bs4
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
        self, html: BeautifulSoup, file_name: str, section_name: str = "", depth: int = 6
    ) -> Union[List[Tuple[epub.Section, List[epub.Link]]], List[epub.Link]]:

        # Validate input, max depth of HTML heading is h6
        if depth > 6:
            depth = 6

        # Catch all the heading HTML tags (h1, ..., h<depth>)
        all_headings: list[bs4.element.Tag] = [heading for heading in html.find_all(re.compile(f"^h[1-{depth}]$"))]

        def _extract_heading_number(heading_tag: bs4.element.Tag) -> int:
            """Extract heading number from html tag i.e. 'h1' -> 1"""
            return int(re.search(f"[1-{depth}]$", heading_tag.name).group(0))  # type: ignore

        def _make_link(tag: bs4.element.Tag) -> epub.Link:
            return epub.Link(href=f"{file_name}#{tag.span['id']}", title=tag.text, uid=tag.span["id"])

        def _make_section(tag: bs4.element.Tag) -> epub.Section:
            return epub.Section(title=tag.text, href=f"{file_name}#{tag.span['id']}")

        all_headings_iterable = iter(all_headings)  # type: ignore

        nested_list: epub.Link | list = []

        # Next build a nested lists structure of a pattern:
        # [<h1 tag>,[<h2 tag>, <h2 tag>, [<h3 tag>], <h2 tag>], <h1 tag>, [<h2 tag>]]
        # Each lower level heading is a nested list
        def _nest_or_extend() -> epub.Link | list | None:
            current_tag = next(all_headings_iterable, None)
            next_tag = next(all_headings_iterable, None)

            if not current_tag:
                return None  # reached the end of list
            elif not next_tag or _extract_heading_number(current_tag) <= _extract_heading_number(next_tag):
                return _make_link(current_tag)
            else:  # next heading is lower level, need to nest
                return [_make_section(current_tag), [_nest_or_extend()]]

        while section := _nest_or_extend():  # loop breaks when iterator next() becomes None
            nested_list.append(section)

        if section_name:
            return [
                (epub.Section(section_name), nested_list),
            ]
        else:
            return nested_list

    def __make_chapter(
        self, html: BeautifulSoup, chapter_number: int, section_name: str = "", make_index: bool = True
    ) -> Tuple[epub.EpubHtml, List[epub.Link] | None]:
        file_name = f"chapter_{chapter_number}.xhtml"
        chapter = self.__make_chapter_content(html, file_name)

        index = _chapter = self.__make_chapter_index(html, file_name, section_name=section_name) if make_index else None

        return chapter, index

    def __set_chapters(
        self,
        book: epub.EpubBook,
        html: BeautifulSoup,
        chapter_number: int,
        section_name: str = "",
        make_index: bool = True,
    ) -> None:
        chapter, index = self.__make_chapter(
            html=html, chapter_number=chapter_number, section_name=section_name, make_index=make_index
        )
        book.add_item(chapter)
        if index:
            book.toc.extend(index)
        book.spine.append(chapter)

    def __generate_epub(self) -> None:
        """Generate epub"""
        log.debug("Generating epub...")

        _volumes_in_html = [BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_html()]  # type: ignore
        frontmatters = [BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_frontmatter().values()]  # type: ignore # TODO: resolve this

        volume_number = 0
        for _config, _html in zip(self.config.edition.volumes, _volumes_in_html):
            book = epub.EpubBook()
            book.spine = [
                "nav",
            ]

            self.__set_metadata(book)
            self.__set_styles(book)

            for _frontmatter in frontmatters:
                volume_number += 1
                self.__set_chapters(book, html=_frontmatter, chapter_number=volume_number, make_index=False)

            volume_number += 1

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
        # self.__generate_endmatter()
        # self.__generate_covers()
        self.__generate_epub()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
