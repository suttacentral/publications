import logging
import os
import tempfile
from copy import copy
from pathlib import Path
from typing import Callable, no_type_check

from bs4 import BeautifulSoup, Tag
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, Link, Section, write_epub

from sutta_publisher.edition_parsers.helper_functions import (
    extract_string,
    find_mainmatter_part_uids,
    find_sutta_title_depth,
    get_chapter_name,
    get_true_volume_index,
    make_section_or_link,
)
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

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

    def _make_chapter(self, html: BeautifulSoup, chapter_name: str) -> EpubHtml:
        file_name = f"{chapter_name}.xhtml"
        return self._make_chapter_content(html=html, file_name=file_name)

    def _set_chapter(self, book: EpubBook, html: BeautifulSoup, chapter_name: str = "") -> None:
        if not chapter_name:
            chapter_name = get_chapter_name(html)
        chapter = self._make_chapter(html=html, chapter_name=chapter_name)
        book.add_item(chapter)
        book.spine.append(chapter)

    def _set_matter_part_chapter(self, book: EpubBook, html: BeautifulSoup) -> None:
        if html.article:
            _id: str = html.article.get("id")
            self._set_chapter(book=book, html=html)
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

    def _make_mainmatter_uids_mapping(self, mainmatter_uids: list[list[str]]) -> dict[str, str]:
        return {uid: chapter[0] for chapter in mainmatter_uids for uid in chapter}

    @staticmethod
    def _process_secondary_toc_links(html: BeautifulSoup, mapping: dict[str, str]) -> None:
        for _tag in html.find_all("a", href=True):
            _tag["href"] = f'{mapping[_tag["href"][1:]]}.xhtml{_tag["href"]}'

    @no_type_check
    @staticmethod
    def _process_links(links: list[Tag], mapping: dict[str, str] = None, chapter_name: str = "") -> None:
        for _tag in links:
            _target: str = chapter_name if chapter_name else mapping.get(_tag["href"][1:], list(mapping.keys())[0])
            _tag["href"] = f'{_target}.xhtml{_tag["href"]}'

    def _set_mainmatter_chapter(self, book: EpubBook, html: BeautifulSoup, volume: Volume, uids: list[str]) -> None:
        _volume_index: int = get_true_volume_index(volume)
        _chapter_name = uids[0]
        self._set_chapter(book=book, html=html, chapter_name=_chapter_name)

    def _set_main_toc(self, volume: Volume, mapping: dict[str, str]) -> list[Link | list[Section | Link]]:
        _index = get_true_volume_index(volume)
        _tree = self.raw_data[_index].tree
        _headings = copy(volume.main_toc.headings)
        return [make_section_or_link(headings=_headings, item=_item, mapping=mapping) for _item in _tree]

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

        # prepare helper data
        _sutta_depth = find_sutta_title_depth(html=BeautifulSoup(volume.mainmatter, "lxml"))
        mainmatter_uids: list[list[str]] = self._get_mainmatter_uids(
            mainmatter_parts=volume_mainmatter, depth=_sutta_depth
        )
        mainmatter_uids_mapping: dict[str, str] = self._make_mainmatter_uids_mapping(mainmatter_uids=mainmatter_uids)

        # set frontmatter
        for _matter_part in volume.frontmatter:
            _frontmatter_part_html: BeautifulSoup = BeautifulSoup(_matter_part, "lxml")

            # skip setting html main toc as chapter
            if _frontmatter_part_html.section and _frontmatter_part_html.section["id"] == "main-toc":
                continue

            # connect blurb links with appropriate chapters
            if _links := _frontmatter_part_html.find_all("a", class_="blurb-link"):
                self._process_links(links=_links, mapping=mainmatter_uids_mapping)

            self._set_chapter(book=book, html=_frontmatter_part_html)

        # set mainmatter
        for _part, _uids in zip(volume_mainmatter, mainmatter_uids):

            # connect secondary toc items to appropriate chapters
            if self.config.edition.secondary_toc and (_section := _part.find("section", class_="secondary-toc")):
                self._process_secondary_toc_links(html=_section, mapping=mainmatter_uids_mapping)

            # connect note references with endnotes chapter
            if _links := _part.find_all("a", role="doc-noteref"):
                self._process_links(links=_links, chapter_name="endnotes")

                # prepare helper data
                for _link in _links:
                    mainmatter_uids_mapping[_link["id"]] = _uids[0]

            self._set_mainmatter_chapter(book=book, html=_part, volume=volume, uids=_uids)

        # set backmatter
        for _part in volume.backmatter:
            _backmatter_part_html: BeautifulSoup = BeautifulSoup(_part, "lxml")

            # connect note backlinks to appropriate chapters
            if _links := _backmatter_part_html.find_all("a", role="doc-backlink"):
                self._process_links(links=_links, mapping=mainmatter_uids_mapping)

            self._set_chapter(book=book, html=_backmatter_part_html)

        # set table of contents
        book.toc.extend(self._set_main_toc(volume=volume, mapping=mainmatter_uids_mapping))

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
