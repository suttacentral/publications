import logging
from copy import copy
from pathlib import Path
from typing import Callable, no_type_check

from bs4 import BeautifulSoup, Tag
from ebooklib.epub import EpubBook, EpubHtml, EpubItem, EpubNav, EpubNcx, Link, Section, write_epub
from wand.image import Image

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
from .latex import LatexParser

log = logging.getLogger(__name__)


class EpubEdition(LatexParser):
    CSS_PATH: Path = Path(__file__).parent.parent / "css_stylesheets/epub.css"

    edition_type: EditionType = EditionType.epub
    default_style: EpubItem
    mainmatter_uids: list[list[str]]
    mainmatter_uids_mapping: dict[str, str]
    sutta_depth: int
    volume_mainmatter: list[BeautifulSoup]

    def _set_metadata(self, book: EpubBook) -> None:
        book.set_identifier(self.config.edition.edition_id)
        book.set_title(self.config.publication.translation_title)
        book.set_language(self.config.publication.translation_lang_iso)
        book.add_author(self.config.publication.creator_name)

    def _set_cover(self, book: EpubBook, volume: Volume) -> None:
        _img_path = (self.TEMP_DIR / volume.cover_filename).with_suffix(".jpg")

        try:
            with open(_img_path, "rb") as img:
                book.set_cover(file_name=f"cover.jpg", content=img.read())
        except FileNotFoundError:
            log.warning(f"File '{str(_img_path)}' not found. Skipping setting epub cover.")

    def _add_image(self, book: EpubBook, file_path: Path) -> None:
        try:
            with open(file_path, "rb") as _img:
                _img = EpubItem(
                    uid=file_path.stem,
                    file_name=f"images/{file_path.name}",
                    media_type=f"image/{file_path.suffix[1:]}",
                    content=_img.read(),
                )
                book.add_item(_img)
        except FileNotFoundError:
            log.warning(f"File '{str(_img)}' not found. Skipping.")

    def _set_default_style(self) -> EpubItem:
        with open(file=self.CSS_PATH) as f:
            EPUB_CSS = f.read()
        return EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=EPUB_CSS)

    def _make_chapter_content(self, html: BeautifulSoup, file_name: str) -> EpubHtml:
        _chapter = EpubHtml(title=self.config.publication.translation_title, file_name=file_name)
        _chapter.content = str(html)
        return _chapter

    def _make_chapter(self, html: BeautifulSoup, chapter_name: str) -> EpubHtml:
        file_name = f"{chapter_name}.xhtml"
        return self._make_chapter_content(html=html, file_name=file_name)

    def _set_chapter(self, book: EpubBook, html: BeautifulSoup, chapter_name: str) -> None:
        chapter = self._make_chapter(html=html, chapter_name=chapter_name)
        chapter.add_item(self.default_style)
        book.add_item(chapter)
        book.spine.append(chapter)

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
                    or (_tag.has_attr("data-split") and "epub" in _tag["data-split"])
                )
            ):
                _tag.insert_after("//split")

        _mainmatter = extract_string(_html)
        return [BeautifulSoup(_part, "lxml") for _part in _mainmatter.split("//split")]

    def _get_mainmatter_uids(self) -> list[list[str]]:
        return [find_mainmatter_part_uids(html=_part, depth=self.sutta_depth) for _part in self.volume_mainmatter]

    def _make_mainmatter_uids_mapping(self) -> dict[str, str]:
        return {uid: chapter[0] for chapter in self.mainmatter_uids for uid in chapter}

    def _set_frontmatter(self, book: EpubBook, volume: Volume) -> None:
        for _matter_part in volume.frontmatter:
            _frontmatter_part_html: BeautifulSoup = BeautifulSoup(_matter_part, "lxml")
            _chapter_name: str = get_chapter_name(_frontmatter_part_html)

            # skip setting html main toc as chapter
            if _chapter_name == "main-toc":
                continue

            # connect blurb links with appropriate chapters
            elif _chapter_name == "blurbs":
                _links = _frontmatter_part_html.find_all("a", class_="blurb-link")
                self._process_links(links=_links)

            self._set_chapter(book=book, html=_frontmatter_part_html, chapter_name=_chapter_name)

    def _set_mainmatter(self, book: EpubBook, volume: Volume) -> None:
        for _part, _uids in zip(self.volume_mainmatter, self.mainmatter_uids):

            # connect secondary toc items to appropriate chapters
            if self.config.edition.secondary_toc and (_section := _part.find("section", class_="secondary-toc")):
                self._process_secondary_toc_links(html=_section)

            # connect note references with endnotes chapter
            if _links := _part.find_all("a", role="doc-noteref"):
                self._process_links(links=_links, chapter_name="endnotes")

                # prepare helper data
                for _link in _links:
                    self.mainmatter_uids_mapping[_link["id"]] = _uids[0]

            self._set_mainmatter_chapter(book=book, html=_part, volume=volume, uids=_uids)

    def _set_backmatter(self, book: EpubBook, volume: Volume) -> None:
        for _part in volume.backmatter:
            _backmatter_part_html: BeautifulSoup = BeautifulSoup(_part, "lxml")
            _chapter_name = get_chapter_name(_backmatter_part_html)

            # connect note backlinks to appropriate chapters
            if _chapter_name == "endnotes":
                _links = _backmatter_part_html.find_all("a", role="doc-backlink")
                self._process_links(links=_links)

            self._set_chapter(book=book, html=_backmatter_part_html, chapter_name=_chapter_name)

    def _process_secondary_toc_links(self, html: BeautifulSoup) -> None:
        for _tag in html.find_all("a", href=True):
            _tag["href"] = f'{self.mainmatter_uids_mapping[_tag["href"][1:]]}.xhtml{_tag["href"]}'

    @no_type_check
    def _process_links(self, links: list[Tag], chapter_name: str = "") -> None:
        for _tag in links:
            _target: str = (
                chapter_name
                if chapter_name
                else self.mainmatter_uids_mapping.get(_tag["href"][1:], list(self.mainmatter_uids_mapping.keys())[0])
            )
            _tag["href"] = f'{_target}.xhtml{_tag["href"]}'

    def _set_mainmatter_chapter(self, book: EpubBook, html: BeautifulSoup, volume: Volume, uids: list[str]) -> None:
        _volume_index: int = get_true_volume_index(volume)
        _chapter_name = uids[0]
        self._set_chapter(book=book, html=html, chapter_name=_chapter_name)

    def _set_main_toc(self, volume: Volume) -> list[Link | list[Section | Link]]:
        _index = get_true_volume_index(volume)
        _tree = self.raw_data[_index].tree
        _headings = copy(volume.main_toc.headings)
        return [
            make_section_or_link(headings=_headings, item=_item, mapping=self.mainmatter_uids_mapping)
            for _item in _tree
        ]

    def generate_epub(self, volume: Volume) -> None:
        log.debug("Generating epub...")

        book = EpubBook()
        book.spine = [
            "nav",
        ]

        # set metadata
        self._set_metadata(book=book)

        # set cover
        self._set_cover(book=book, volume=volume)

        # set style
        self.default_style = self._set_default_style()
        book.add_item(self.default_style)

        # add halftitle page image
        self._add_image(book=book, file_path=self.IMAGES_DIR / "sclogo.png")

        # divide mainmatter into separate chapters
        self.volume_mainmatter = self._split_mainmatter(mainmatter=volume.mainmatter)

        # prepare helper data
        self.sutta_depth = find_sutta_title_depth(html=BeautifulSoup(volume.mainmatter, "lxml"))
        self.mainmatter_uids = self._get_mainmatter_uids()
        self.mainmatter_uids_mapping = self._make_mainmatter_uids_mapping()

        # set frontmatter
        self._set_frontmatter(book=book, volume=volume)

        # set mainmatter
        self._set_mainmatter(book=book, volume=volume)

        # set backmatter
        self._set_backmatter(book=book, volume=volume)

        # set table of contents
        book.toc.extend(self._set_main_toc(volume=volume))

        # add navigation files
        book.add_item(EpubNcx())
        book.add_item(EpubNav())

        # create epub file
        _path = (self.TEMP_DIR / volume.filename).with_suffix(".epub")
        write_epub(name=_path, book=book, options={})

        self.append_file_paths(volume=volume, paths=[_path])

    def generate_cover(self, volume: Volume) -> None:
        log.debug("Generating cover...")

        _path = self.TEMP_DIR / volume.cover_filename
        log.debug("Generating tex...")
        doc = self._generate_cover(volume=volume, preamble="preamble", body="body", template_dir="individual")
        # doc.generate_tex(filepath=str(_path))  # dev
        log.debug("Generating pdf...")
        doc.generate_pdf(filepath=str(_path), clean_tex=False, compiler="latexmk", compiler_args=["-lualatex"])

        self.append_file_paths(volume=volume, paths=[_path.with_suffix(".tex"), _path.with_suffix(".pdf")])

    def convert_cover_to_jpg(self, volume: Volume) -> None:
        log.debug("Converting pdf to jpg...")

        _path = self.TEMP_DIR / volume.cover_filename
        with Image(filename=f"pdf:{_path.with_suffix('.pdf')}", resolution=self.IMAGE_DENSITY) as img:
            img.format = "jpeg"
            img.compression_quality = self.IMAGE_QUALITY
            img.save(filename=_path.with_suffix(".jpg"))

        self.append_file_paths(volume=volume, paths=[_path.with_suffix(".jpg")])

    def collect_all(self) -> EditionResult:
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [
            self.generate_cover,
            self.convert_cover_to_jpg,
            self.generate_epub,
        ]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        return EditionResult(
            volumes=[volume.file_paths for volume in _edition.volumes],
            creator_uid=self.config.publication.creator_uid,
            text_uid=self.config.edition.text_uid,
            publication_type=self.config.edition.publication_type,
            translation_lang_iso=self.config.publication.translation_lang_iso,
            translation_title=self.config.publication.translation_title,
        )
