import logging
import os
import re
import tempfile
from collections import namedtuple
from typing import Literal

import bs4
from bs4 import BeautifulSoup
from ebooklib import epub

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser

log = logging.getLogger(__name__)

HEADINGS_LITERAL = Literal["h1", "h2", "h3", "h4", "h5", "h6"]

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
    ) -> list[tuple[epub.Section, list[list[epub.Section] | epub.Link]]] | list[list[epub.Section] | epub.Link]:

        # Validate input, max depth of HTML heading is h6
        if depth > 6:
            depth = 6

        # Catch all the heading HTML tags (h1, ..., h<depth>)
        all_headings: list[bs4.element.Tag] = [heading for heading in html.find_all(re.compile(f"^h[1-{depth}]$"))]

        HeadingsIndexTreeFrozen = namedtuple(
            "HeadingsIndexTreeFrozen", ["h1", "h2", "h3", "h4", "h5", "h6"]
        )  # this is needed for dictionary building, as dictionary keys must be immutable

        heading_index = [0, 0, 0, 0, 0, 0]

        def _update_index(heading_tag: bs4.element.Tag) -> None:
            # increment index for this heading level e.g. [1, 1, 2+1, 0, 0, 0] - added another h3
            heading_index[_extract_heading_number(heading_tag) - 1] += 1

            # When adding another heading all lower level headings counters are reset
            for i in range(_extract_heading_number(heading_tag), 6):
                heading_index[i] = 0

        def _extract_heading_number(heading_tag: bs4.element.Tag) -> int:
            """Extract heading number from html tag i.e. 'h1' -> 1"""
            return int(re.search(f"[1-{depth}]$", heading_tag.name).group(0))  # type: ignore

        # Build a tree of headings where structure is represented by tuple of indexes
        headings_tree: dict[HeadingsIndexTreeFrozen, bs4.element.Tag] = {}
        for heading in all_headings:
            _update_index(heading)
            # This freezes and copies the current state of heading_index even though it is used in further iterations
            headings_tree.update({HeadingsIndexTreeFrozen(*heading_index): heading})

        def _make_link(tag: bs4.element.Tag) -> epub.Link:
            return epub.Link(href=f"{file_name}#{tag.span['id']}", title=tag.text, uid=tag.span["id"])

        def _make_section(tag: bs4.element.Tag) -> epub.Section:
            return epub.Section(title=tag.text, href=f"{file_name}#{tag.span['id']}")

        def _find_index_root(_index: HeadingsIndexTreeFrozen) -> tuple[int, ...]:
            """Find common index root for all children of this heading - i.e. a non-zero subset of this tuple"""
            return tuple([i for i in _index if i != 0])

        def _compare_index_against_root(_index: HeadingsIndexTreeFrozen, root: tuple[int, ...]) -> bool:
            """Return True if index is in a given root (heading is a child of superheading with that root)"""
            for i, counter in enumerate(root):
                if counter != _index[i]:
                    return False
            return True

        def _find_children_by_index(
            _index: HeadingsIndexTreeFrozen,
        ) -> list[tuple[HeadingsIndexTreeFrozen, bs4.element.Tag]]:
            """Based on parents index, find all children headings"""
            parent_root = _find_index_root(_index)
            # Return all indexes with the same root except for the parent
            return [
                (child_index, potential_child)
                for child_index, potential_child in headings_tree.items()
                if _compare_index_against_root(_index=child_index, root=parent_root) and child_index != _index
            ]

        def _make_section_or_link(
            _index: HeadingsIndexTreeFrozen, heading: bs4.element.Tag
        ) -> list[epub.Section] | epub.Link:
            """Look up heading's children and accordingly create link or section recursively"""
            _children: list[tuple[HeadingsIndexTreeFrozen, bs4.element.Tag]] = _find_children_by_index(_index)
            # Heading has children (subheadings), so it's an epub.Section
            if _children:
                return [_make_section(heading), [_make_section_or_link(*child) for child in _children]]
            else:
                return _make_link(heading)

        # Time to create the output list. Loop only through top level headings, subheadings will be handled recursively by the function
        top_level_headings = [
            (index, heading) for index, heading in headings_tree.items() if len(_find_index_root(index)) == 1
        ]  # top level headings are heading with only h1 counter != 0

        toc_as_list = [_make_section_or_link(*top_level_heading) for top_level_heading in top_level_headings]

        if section_name:
            return [
                (epub.Section(section_name), toc_as_list),
            ]
        else:
            return toc_as_list

    def __make_chapter(
        self, html: BeautifulSoup, chapter_number: int, section_name: str = "", make_index: bool = True
    ) -> tuple[epub.EpubHtml, list[epub.Link] | None]:
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
        frontmatters = [
            BeautifulSoup(_, "lxml") for _ in self._EditionParser__generate_frontmatter().values()  # type: ignore
        ]  # type: ignore # TODO: resolve this

        volume_number = 0
        for _config, _html in zip(self.config.edition.volumes, _volumes_in_html):
            volume_number = +1
            book = epub.EpubBook()
            book.spine = [
                "nav",
            ]

            self.__set_metadata(book)
            self.__set_styles(book)

            for _frontmatter in frontmatters:
                self.__set_chapters(book, html=_frontmatter, chapter_number=volume_number, make_index=False)
                volume_number = +1

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
