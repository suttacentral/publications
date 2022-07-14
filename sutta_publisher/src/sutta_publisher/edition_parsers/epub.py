import logging
import os
import tempfile
from copy import copy
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, Link, Section, write_epub

from sutta_publisher.edition_parsers.helper_functions import (
    extract_string,
    find_mainmatter_part_uids,
    find_sutta_title_depth,
    get_chapter_name,
    make_section_or_link,
)
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

    def _make_reference_links(self, html: BeautifulSoup, chapter_name: str) -> None:
        # TODO: ZNALEŹĆ SPOSÓB NA POŁĄCZENIE BLURBS I ENDNOTES Z POSZCZEGÓLNYMI MAINMATTER (PODZIELIĆ MAINMATTER I ZNALEŹĆ UID PRZED GENEROWANIEM FRONTMATTER W _generate_epub())
        if chapter_name == "blurbs":
            _links = html.find_all("a", class_="blurb-link")
            _target_chapter = "mainmatter"
        elif chapter_name == "mainmatter":
            _links = html.find_all("a", role="doc-noteref")
            _target_chapter = "endnotes"
        else:
            _links = html.find_all("a", href=lambda x: x and x.startswith("#"))
            _target_chapter = "mainmatter"

        for _link in _links:
            # skip if link is an element of the chapter's contents list
            if _link.find_parent("nav", class_="contents"):
                continue
            else:
                _link["href"] = f'{_target_chapter}.xhtml{_link["href"]}'

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

    def _make_chapter(self, html: BeautifulSoup, chapter_name: str) -> EpubHtml:
        self._make_reference_links(html=html, chapter_name=chapter_name)
        file_name = f"{chapter_name}.xhtml"
        return self._make_chapter_content(html=html, file_name=file_name)

    def _set_chapter(
        self,
        book: EpubBook,
        html: BeautifulSoup,
        section_name: str = "",
        chapter_name: str = "",
        headings: list[ToCHeading] = None,
        tree: list[dict | str] | None = None,
    ) -> None:
        if not chapter_name:
            chapter_name = get_chapter_name(html)
        chapter = self._make_chapter(html=html, chapter_name=chapter_name)
        book.add_item(chapter)
        # TODO: REMOVE
        # if headings:
        #     toc = EpubEdition._make_chapter_toc(
        #         headings=headings,
        #         file_name=f"{chapter_name}.xhtml",
        #         tree=tree,
        #         section_name=section_name,
        #     )
        #     book.toc.extend(toc)
        book.spine.append(chapter)

    def _set_matter_part_chapter(self, book: EpubBook, html: BeautifulSoup, volume: Volume) -> None:
        if html.article:
            _id: str = html.article.get("id")
            _heading: list[ToCHeading] | None = next(([h] for h in volume.main_toc.headings if h.uid == _id), None)
            self._set_chapter(book=book, html=html, headings=_heading)
        else:
            self._set_chapter(book=book, html=html)

    def _split_mainmatter(self, mainmatter: str) -> list[BeautifulSoup]:
        _html: BeautifulSoup = BeautifulSoup(mainmatter, "lxml")
        for _tag in _html.find("body").children:

            if (
                _tag.name
                and _tag.name in ("article", "section")
                and _tag.next_sibling
                and (
                    (_tag.next_sibling.has_attr("class") and "section-title" in _tag.next_sibling["class"])
                    or (_tag.has_attr("class") and "secondary-toc" in _tag["class"])
                )
            ):
                _tag.insert_after("//split")

        _mainmatter = extract_string(_html)
        return [BeautifulSoup(_part, "lxml") for _part in _mainmatter.split("//split")]

    def _get_mainmatter_uids(self, mainmatter_parts: list[BeautifulSoup], depth: int) -> list[list[str]]:
        return [find_mainmatter_part_uids(html=_part, depth=depth) for _part in mainmatter_parts]

    def _set_mainmatter_chapter(
        self,
        book: EpubBook,
        html: BeautifulSoup,
        volume: Volume,
        uids: list[str],
    ) -> None:
        _volume_index: int = self._get_true_index(volume)
        _chapter_name = uids[0]
        # _tree: list[dict | str] = [self.raw_data[_volume_index].tree[index]]
        # _headings: list[ToCHeading] = [_heading for _heading in volume.main_toc.headings if _heading.uid in uids]
        self._set_chapter(book=book, html=html, chapter_name=_chapter_name)

    def _generate_epub(self, volume: Volume) -> None:
        log.debug("Generating epub...")

        book = EpubBook()
        book.spine = [
            "nav",
        ]

        # set metadata
        self._set_metadata(book)
        self._set_styles(book)

        # divide mainmatter into separate chapters
        volume_mainmatter: list[BeautifulSoup] = self._split_mainmatter(mainmatter=volume.mainmatter)
        _sutta_depth = find_sutta_title_depth(html=BeautifulSoup(volume.mainmatter, "lxml"))
        mainmatter_uids: list[list[str]] = self._get_mainmatter_uids(
            mainmatter_parts=volume_mainmatter,
            depth=_sutta_depth,
        )

        # set frontmatter
        for _matter_part in volume.frontmatter:
            _frontmatter_part_html: BeautifulSoup = BeautifulSoup(_matter_part, "lxml")

            # Skip adding HTML main table of contents
            if _frontmatter_part_html.section and _frontmatter_part_html.section["id"] == "main-toc":
                continue

            self._set_matter_part_chapter(book=book, html=_frontmatter_part_html, volume=volume)

        # set mainmatter
        for _part, _uids in zip(volume_mainmatter, mainmatter_uids):
            self._set_mainmatter_chapter(book=book, html=_part, volume=volume, uids=_uids)

        # set backmatter
        for _part in volume.backmatter:
            _backmatter_part_html: BeautifulSoup = BeautifulSoup(_part, "lxml")
            self._set_matter_part_chapter(book=book, html=_backmatter_part_html, volume=volume)

        # set table of contents

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
