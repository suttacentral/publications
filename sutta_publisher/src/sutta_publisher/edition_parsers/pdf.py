import logging
import os.path
import tempfile
from typing import Callable, cast

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from pylatex import Document, NewPage, NoEscape
from pylatex.base_classes import Command, Environment
from pylatex.package import Package
from pylatex.utils import italic

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf
    endnotes: list[str] | None

    def _append_paragraph(self, doc: Document, tag: Tag) -> str:
        tex: str = ""
        if tag.has_attr("id"):
            tex += Command("marginnote", tag["id"], tag["id"]).dumps()
        tex += self._process_contents(doc=doc, contents=tag.contents)
        if tag.next_sibling:
            tex += NoEscape("\n\n")
        return tex

    def _append_verse(self, doc: Document, tag: Tag) -> str:
        verse: Environment = Environment()
        verse._latex_name = "verse"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        verse.append(NoEscape(_data))
        return cast(str, verse.dumps())

    def _append_quotation(self, doc: Document, tag: Tag) -> str:
        quotation: Environment = Environment()
        quotation._latex_name = "quotation"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        quotation.append(NoEscape(_data))
        return cast(str, quotation.dumps())

    @staticmethod
    def _append_breakline() -> str:
        return cast(str, NoEscape(r"\\") + NoEscape("\n"))

    @staticmethod
    def _append_emphasis(tag: Tag) -> str:
        return cast(str, NoEscape(rf"\emph{{{tag.string}}}"))

    @staticmethod
    def _append_roman_script_macro(tag: Tag) -> str:
        return cast(str, italic(tag.string))

    @staticmethod
    def _append_other_script_macro(tag: Tag) -> str:
        return cast(str, NoEscape(rf'\text{tag["lang"]}{{{tag.string}}}'))

    def _append_footnote(self, doc: Document, tag: Tag) -> str:
        if self.endnotes:
            _index: int = int(tag.string)
            _note_contents: list[PageElement] = BeautifulSoup(self.endnotes[_index - 1], "lxml").body.contents
            _data: str = self._process_contents(doc=doc, contents=_note_contents)
            return cast(str, Command("footnote", NoEscape(_data)).dumps())
        else:
            return ""

    @staticmethod
    def _append_section(tag: Tag) -> str:
        tex: str = ""
        _title: str = " ".join(tag.stripped_strings)
        tex += Command("section*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "section", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n")
        return tex

    @staticmethod
    def _append_chapter(tag: Tag) -> str:
        tex: str = ""
        _title: str = tag.string
        tex += Command("chapter*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "chapter", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n")
        return tex

    @staticmethod
    def _append_new_page() -> str:
        return cast(str, NewPage().dumps())

    @staticmethod
    def _append_tableofcontents() -> str:
        return cast(str, Command("tableofcontents").dumps())

    def _append_epigraph(self, doc: Document, tag: Tag) -> str:
        _text_tag, _source_tag = tag.find_all("p")
        _text: str = NoEscape(self._process_tag(doc=doc, tag=_text_tag))
        _source: str = italic(NoEscape(self._process_tag(doc=doc, tag=_source_tag)))
        return cast(str, Command("epigraph", arguments=[_text, _source]).dumps())

    def _process_tag(self, doc: Document, tag: Tag) -> str:
        if tag.name == "p":
            return self._append_paragraph(doc, tag)

        elif tag.name == "blockquote":
            if tag.has_attr("class") and "gatha" in tag["class"]:
                return self._append_verse(doc, tag)
            else:
                return self._append_quotation(doc, tag)

        elif tag.name == "br":
            return self._append_breakline()

        elif tag.name == "em":
            return self._append_emphasis(tag)

        elif tag.name == "i":
            if tag.has_attr("lang") and any(_lang in tag["lang"] for _lang in ["pi", "san"]):
                return self._append_roman_script_macro(tag)
            else:
                return self._append_other_script_macro(tag)

        elif tag.has_attr("role") and "doc-noteref" in tag["role"]:
            return self._append_footnote(doc, tag)

        elif tag.name == "h2" and tag.has_attr("class") and "sutta-title" in tag["class"]:
            return self._append_section(tag)

        elif tag.name == "h1":
            return self._append_chapter(tag)

        elif tag.has_attr("id") and tag["id"] in self.new_pages:
            return self._append_new_page()

        elif tag.has_attr("id") and tag["id"] == "main-toc":
            return self._append_tableofcontents()

        elif tag.has_attr("class") and "epigraph" in tag["class"]:
            return self._append_epigraph(doc, tag)

        else:
            return self._process_contents(doc=doc, contents=tag.contents)

    def _process_contents(self, doc: Document, contents: list[PageElement]) -> str:
        tex: str = ""

        for _element in contents:
            if isinstance(_element, Tag):
                tex += self._process_tag(doc=doc, tag=_element)
            elif isinstance(_element, NavigableString) and _element != "\n":
                tex += _element

        return tex

    def _generate_latex(self, volume: Volume) -> Document:
        # setup
        self.endnotes: list[str] | None = volume.endnotes if volume.endnotes else None
        self.new_pages: list[str] = ["imprint", "halftitlepage"]

        doc = Document(documentclass="book")

        # set packages
        doc.packages.append(Package("marginnote"))

        # set frontmatter
        doc.append(Command("frontmatter"))
        for _part in volume.frontmatter:
            _element = BeautifulSoup(_part, "lxml").find("body").next_element
            if isinstance(_element, Tag):
                doc.append(NoEscape(self._process_tag(doc=doc, tag=_element)))
            elif isinstance(_element, NavigableString) and _element != "\n":
                doc.append(_element)

        # set mainmatter
        doc.append(Command("mainmatter"))
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml").find("body")
        for _element in _mainmatter:
            if isinstance(_element, Tag):
                doc.append(NoEscape(self._process_tag(doc=doc, tag=_element)))
            elif isinstance(_element, NavigableString) and _element != "\n":
                doc.append(_element)

        # set backmatter
        doc.append(Command("backmatter"))
        for _part in volume.backmatter:
            _element = BeautifulSoup(_part, "lxml").find("body").next_element
            if isinstance(_element, Tag):
                doc.append(NoEscape(self._process_tag(doc=doc, tag=_element)))
            elif isinstance(_element, NavigableString) and _element != "\n":
                doc.append(_element)

        return doc

    def _generate_pdf(self, volume: Volume) -> None:
        log.debug("Generating pdf...")

        _path: str = os.path.join(tempfile.gettempdir(), volume.filename[:-4])
        doc = self._generate_latex(volume=volume)
        doc.generate_tex(filepath=_path)
        # doc.generate_pdf(filepath=_path, clean_tex=False, compiler="latexmk")

    def collect_all(self):  # type: ignore
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [self._generate_pdf]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        # self.generate_pdf()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
