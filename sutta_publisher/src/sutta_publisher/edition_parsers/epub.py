import logging
import os
import tempfile
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from ebooklib import epub
from ebooklib.epub import Link, Section

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData

from .base import EditionParser
from .helper_functions import HeadingsIndexTreeFrozen, _find_index_root, make_headings_tree, make_section_or_link

log = logging.getLogger(__name__)

CSS_PATH = Path(__file__).parent / "css_stylesheets/epub.css"
with open(file=CSS_PATH) as f:
    EPUB_CSS = f.read()


class EpubEdition(EditionParser):
    edition_type = EditionType.epub

    # We need an overridden init to collect headings for ToC
    def __init__(self, config: EditionConfig, data: EditionData):
        super().__init__(config, data)
        self.__generate_toc()

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

    @staticmethod
    def __make_chapter_toc(
        headings: list[Tag], file_name: str, section_name: str = ""
    ) -> list[tuple[Section, list[list[Section] | Link]]] | list[list[Section] | Link]:

        headings_tree: dict[HeadingsIndexTreeFrozen, Tag] = make_headings_tree(chapter_headings=headings)

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
        self, html: BeautifulSoup, chapter_number: int, section_name: str = "", make_index: bool = True
    ) -> Tuple[epub.EpubHtml, List[epub.Link] | None]:
        file_name = f"chapter_{chapter_number}.xhtml"
        chapter = self.__make_chapter_content(html, file_name)

        index = EpubEdition.__make_chapter_toc(html, file_name, section_name=section_name) if make_index else None

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

        frontmatters = [
            BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_frontmatter().values()  # type: ignore  # TODO: resolve this
        ]

        volume_number = 0
        for _config, _html in zip(self.config.edition.volumes, self.per_volume_html):
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
