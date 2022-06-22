import logging
import os
import tempfile
from copy import copy
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, Link, Section, write_epub

from sutta_publisher.edition_parsers.helper_functions import make_section_or_link
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, ToCHeading, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class EpubEdition(EditionParser):
    CSS_PATH: Path = Path(__file__).parent.parent / "css_stylesheets/epub.css"
    edition_type: EditionType = EditionType.epub

    def _set_metadata(self, book: EpubBook) -> None:
        book.set_identifier(self.config.edition.edition_id)
        book.set_title(self.config.publication.translation_title)
        book.set_language(self.config.publication.translation_lang_iso)
        book.add_author(self.config.publication.creator_name)

    def _set_styles(self, book: EpubBook) -> None:
        with open(file=self.CSS_PATH) as f:
            EPUB_CSS = f.read()
        default_css = EpubItem(
            uid="style_default", file_name="style/default.css", media_type="text/css", content=EPUB_CSS
        )
        book.add_item(default_css)

    def _make_chapter_content(self, html: BeautifulSoup, file_name: str) -> EpubHtml:
        _chapter = EpubHtml(title=self.config.publication.translation_title, file_name=file_name)
        _chapter.content = str(html)
        return _chapter

    @staticmethod
    def _make_chapter_toc(
        headings: list[ToCHeading],
        file_name: str,
        tree: list[dict | str],
        section_name: str = "",
    ) -> list[tuple[Section, list[list[Section] | Link]]] | list[list[Section] | Link]:

        _headings = copy(headings)
        chapter_toc = [make_section_or_link(_headings, item, file_name) for item in tree]

        if section_name:
            return [
                (Section(section_name), chapter_toc),
            ]
        else:
            return chapter_toc

    def _make_chapter(
        self,
        html: BeautifulSoup,
        chapter_number: int,
    ) -> EpubHtml:
        file_name = f"chapter_{chapter_number}.xhtml"
        return self._make_chapter_content(html=html, file_name=file_name)

    def _set_chapter(
        self,
        book: EpubBook,
        html: BeautifulSoup,
        chapter_number: int,
        section_name: str = "",
        headings: list[ToCHeading] = None,
        tree: list[dict | str] = None,
    ) -> None:
        chapter = self._make_chapter(html=html, chapter_number=chapter_number)
        book.add_item(chapter)
        if headings and tree:
            toc = EpubEdition._make_chapter_toc(
                headings=headings,
                file_name=f"chapter_{chapter_number}.xhtml",
                tree=tree,
                section_name=section_name,
            )
            book.toc.extend(toc)
        book.spine.append(chapter)

    def _generate_epub(self, volume: Volume) -> None:
        log.debug("Generating epub...")

        book = EpubBook()
        book.spine = [
            "nav",
        ]

        # set metadata
        self._set_metadata(book)
        self._set_styles(book)

        _chapter_number = 0

        # TODO: fix - add generating ToCs for front and backmatters
        # set frontmatter
        for _matter in volume.frontmatter:
            _matter_html: BeautifulSoup = BeautifulSoup(_matter, "lxml")
            _chapter_number += 1
            self._set_chapter(book=book, html=_matter_html, chapter_number=_chapter_number)

        # set mainmatter
        _chapter_number += 1
        _mainmatter: BeautifulSoup = BeautifulSoup(volume.mainmatter, "lxml")
        _filtered_headings = list(filter(lambda heading: heading.type in ["branch", "leaf"], volume.main_toc.headings))
        _index = self._get_true_index(volume)
        _tree = self.raw_data[_index].tree
        self._set_chapter(
            book=book, html=_mainmatter, headings=_filtered_headings, chapter_number=_chapter_number, tree=_tree
        )

        # set backmatter
        for _matter in volume.backmatter:
            _matter_html = BeautifulSoup(_matter, "lxml")
            _chapter_number += 1
            self._set_chapter(book=book, html=_matter_html, chapter_number=_chapter_number)

        # add navigation files
        book.add_item(EpubNcx())
        book.add_item(EpubNav())

        # create epub file
        _path: str = os.path.join(tempfile.gettempdir(), volume.filename)
        write_epub(name=_path, book=book, options={})

    def collect_all(self) -> EditionResult:
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [self.set_cover, self._generate_epub]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        # self._generate_covers()
        # self._generate_epub()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
