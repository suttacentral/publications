import logging
import os
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, Link, Section, write_epub

from sutta_publisher.edition_parsers.helper_functions import (
    HeadingsIndexTreeFrozen,
    _find_index_root,
    make_headings_tree,
    make_section_or_link,
)
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser

log = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "css_stylesheets/epub.css"


class EpubEdition(EditionParser):
    edition_type = EditionType.epub

    def __set_metadata(self, book: EpubBook) -> None:
        book.set_identifier(self.config.edition.edition_id)
        book.set_title(self.config.publication.translation_title)
        book.set_language(self.config.publication.translation_lang_iso)
        book.add_author(self.config.publication.creator_name)

    def __set_styles(self, book: EpubBook) -> None:
        with open(file=CSS_PATH) as f:
            EPUB_CSS = f.read()
        default_css = EpubItem(
            uid="style_default", file_name="style/default.css", media_type="text/css", content=EPUB_CSS
        )
        book.add_item(default_css)

    def __make_chapter_content(self, html: BeautifulSoup, file_name: str) -> EpubHtml:
        _chapter = EpubHtml(title=self.config.publication.translation_title, file_name=file_name)
        _chapter.content = str(html)
        return _chapter

    @staticmethod
    def __make_chapter_toc(
        headings: list[Tag], file_name: str, section_name: str = ""
    ) -> list[tuple[Section, list[list[Section] | Link]]] | list[list[Section] | Link]:

        headings_tree: dict[HeadingsIndexTreeFrozen, Tag] = make_headings_tree(headings=headings)

        # Time to create the output list. Loop only through top level headings, subheadings will be handled recursively by the function
        top_level_headings = [
            index for index in headings_tree.keys() if len(_find_index_root(index)) == 1
        ]  # top level headings are heading with only h1 counter != 0
        toc_as_list = [
            make_section_or_link(index=index, headings_tree=headings_tree, file_name=file_name)
            for index in top_level_headings
        ]

        if section_name:
            return [
                (Section(section_name), toc_as_list),
            ]
        else:
            return toc_as_list

    def __make_chapter(
        self,
        html: BeautifulSoup,
        chapter_number: int,
    ) -> EpubHtml:
        file_name = f"chapter_{chapter_number}.xhtml"
        return self.__make_chapter_content(html=html, file_name=file_name)

    def __set_chapters(
        self,
        book: EpubBook,
        html: BeautifulSoup,
        headings: list[Tag],
        chapter_number: int,
        section_name: str = "",
        make_index: bool = True,
    ) -> None:
        chapter = self.__make_chapter(html=html, chapter_number=chapter_number)
        book.add_item(chapter)
        if make_index:
            toc = EpubEdition.__make_chapter_toc(
                headings=headings, file_name=f"chapter_{chapter_number}.xhtml", section_name=section_name
            )
            book.toc.extend(toc)
        book.spine.append(chapter)

    def __generate_epub(self) -> None:
        """Generate epub"""
        log.debug("Generating epub...")

        frontmatters = [BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_frontmatter().values()]  # type: ignore

        volume_number = 0
        # We loop over volumes. Each volume is a separate file
        for _config, _html, _main_toc_headings in zip(
            self.config.edition.volumes,
            self.per_volume_html,
            self._EditionParser__collect_main_toc_headings(),  # type: ignore
        ):
            book = EpubBook()
            book.spine = [
                "nav",
            ]

            self.__set_metadata(book)
            self.__set_styles(book)

            for _frontmatter in frontmatters:
                volume_number += 1
                self.__set_chapters(
                    book=book,
                    html=_frontmatter,
                    headings=_main_toc_headings,
                    chapter_number=volume_number,
                    make_index=False,
                )

            volume_number += 1

            self.__set_chapters(book, html=_html, headings=_main_toc_headings, chapter_number=volume_number)

            # add navigation files
            book.add_item(EpubNcx())
            book.add_item(EpubNav())

            _path = os.path.join(
                tempfile.gettempdir(), f"{self.config.publication.translation_title} vol {volume_number}.epub"
            )
            # create epub file
            write_epub(_path, book, {})

    def collect_all(self) -> EditionResult:
        # self.__generate_endmatter()
        # self.__generate_covers()
        self.__generate_epub()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
