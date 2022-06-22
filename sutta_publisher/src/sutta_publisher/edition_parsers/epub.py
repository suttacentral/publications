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
        tree: list[dict | str] | None,
        section_name: str = "",
    ) -> list[tuple[Section, list[list[Section] | Link]]] | list[list[Section] | Link]:

        # Firstly, we need a copy of headings as we will be poping items out
        _headings = copy(headings)

        # Time to create output list. Loop only through top level heading uids, lower levels will be handled recursively
        if tree:
            chapter_toc = [make_section_or_link(_headings, item, file_name) for item in tree]

        # if not tree, it means that we are making chapter toc for frontmatter or backmatter. Loop through headings
        else:
            chapter_toc = [make_section_or_link(_headings, item.uid, file_name) for item in headings]

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
        tree: list[dict | str] | None = None,
    ) -> None:
        chapter = self._make_chapter(html=html, chapter_number=chapter_number)
        book.add_item(chapter)
        if headings:
            toc = EpubEdition._make_chapter_toc(
                headings=headings,
                file_name=f"chapter_{chapter_number}.xhtml",
                tree=tree,
                section_name=section_name,
            )
            book.toc.extend(toc)
        book.spine.append(chapter)

    def _set_matter_part_chapter(
        self, book: EpubBook, html: BeautifulSoup, chapter_number: int, volume: Volume
    ) -> None:
        if html.article:
            _id: str = html.article.get("id")
            _heading: list[ToCHeading] | None = next(([h] for h in volume.main_toc.headings if h.uid == _id), None)
            self._set_chapter(book=book, html=html, headings=_heading, chapter_number=chapter_number)
        else:
            self._set_chapter(book=book, html=html, chapter_number=chapter_number)

    def _set_mainmatter_chapter(self, book: EpubBook, html: BeautifulSoup, chapter_number: int, volume: Volume) -> None:
        _headings: list[ToCHeading] = list(
            filter(lambda heading: heading.type in ["branch", "leaf"], volume.main_toc.headings)
        )
        _index: int = self._get_true_index(volume)
        _tree: list[dict | str] = self.raw_data[_index].tree
        self._set_chapter(book=book, html=html, headings=_headings, chapter_number=chapter_number, tree=_tree)

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

        # set frontmatter
        for _matter_part in volume.frontmatter:
            _frontmatter_part_html: BeautifulSoup = BeautifulSoup(_matter_part, "lxml")
            _chapter_number += 1
            self._set_matter_part_chapter(
                book=book, html=_frontmatter_part_html, chapter_number=_chapter_number, volume=volume
            )

        # set mainmatter
        _chapter_number += 1
        _mainmatter: BeautifulSoup = BeautifulSoup(volume.mainmatter, "lxml")
        self._set_mainmatter_chapter(book=book, html=_mainmatter, chapter_number=_chapter_number, volume=volume)

        # set backmatter
        for _part in volume.backmatter:
            _backmatter_part_html: BeautifulSoup = BeautifulSoup(_part, "lxml")
            _chapter_number += 1
            self._set_matter_part_chapter(
                book=book, html=_backmatter_part_html, chapter_number=_chapter_number, volume=volume
            )

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
