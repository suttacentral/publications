import ast
import logging
import os.path
import tempfile
from pathlib import Path
from typing import Callable, cast

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from jinja2 import Environment as jinja2_Environment, FileSystemLoader, Template, TemplateNotFound
from pylatex import Document, NoEscape
from pylatex.base_classes import Command, Environment
from pylatex.package import Package
from pylatex.utils import bold, italic

from sutta_publisher.edition_parsers.latex_constants import MATTERS_TO_SKIP, NEW_COMMANDS, STYLING_CLASSES
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)

MATTERS_WITH_TEX_TEMPLATES = [
    "titlepage",
    "imprint",
    "halftitlepage",
]
TEX_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "tex"


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf
    endnotes: list[str] | None

    def _append_paragraph(self, doc: Document, tag: Tag) -> str:
        tex: str = ""

        if tag.has_attr("id"):
            tex += Command("marginnote", tag["id"], tag["id"]).dumps()

        tex += self._process_contents(doc=doc, contents=tag.contents)

        if tag.has_attr("class"):
            for _class in tag["class"]:
                if _class in STYLING_CLASSES:
                    tex = Command(f'sc{_class.replace("-", "")}', NoEscape(tex)).dumps()

        if tag.next_sibling:
            tex += "\n\n"

        return cast(str, tex)

    def _append_span(self, doc: Document, tag: Tag) -> str:
        tex = self._process_contents(doc=doc, contents=tag.contents)

        if tag.has_attr("class"):
            for _class in tag["class"]:
                if _class in STYLING_CLASSES:
                    tex = Command(f'sc{_class.replace("-", "")}', NoEscape(tex)).dumps()

        return cast(str, tex)

    def _append_verse(self, doc: Document, tag: Tag) -> str:
        verse_env: Environment = Environment()
        verse_env._latex_name = "verse"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        verse_env.append(_data)
        return cast(str, verse_env.dumps() + NoEscape("\n"))

    def _append_quotation(self, doc: Document, tag: Tag) -> str:
        quotation_env: Environment = Environment()
        quotation_env._latex_name = "quotation"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        quotation_env.append(_data)
        return cast(str, quotation_env.dumps() + NoEscape("\n"))

    @staticmethod
    def _append_breakline() -> str:
        return cast(str, NoEscape(r"\\") + NoEscape("\n"))

    def _append_bold(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, bold(_tex))

    def _append_emphasis(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, Command("emph", _tex).dumps())

    def _append_italic(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, italic(_tex))

    def _append_foreign_script_macro(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, Command(f'text{tag["lang"]}', _tex).dumps())

    def _append_footnote(self, doc: Document, tag: Tag) -> str:
        if self.endnotes:
            _index: int = int(tag.string)
            _note_contents: list[PageElement] = BeautifulSoup(self.endnotes[_index - 1], "lxml").body.contents
            _data: str = self._process_contents(doc=doc, contents=_note_contents)
            return cast(str, Command("footnote", _data).dumps())
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
    def _append_tableofcontents() -> str:
        return cast(str, Command("tableofcontents").dumps())

    def _append_epigraph(self, doc: Document, tag: Tag) -> str:
        _text_tag, _source_tag = tag.find_all("p")
        _text: str = NoEscape(self._process_tag(doc=doc, tag=_text_tag))
        _source: str = italic(NoEscape(self._process_tag(doc=doc, tag=_source_tag)))
        return cast(str, Command("epigraph", arguments=[_text, _source]).dumps())

    def _append_list(self, doc: Document, tag: Tag) -> str:
        _command: str = Command("item").dumps()
        _types = {"ol": "enumerate", "ul": "itemize"}
        list_env: Environment = Environment()
        list_env._latex_name = _types[tag.name]
        for _li in tag.find_all("li"):
            _item: str = self._process_contents(doc=doc, contents=_li.contents)
            list_env.append(NoEscape(f"{_command} {_item}"))
        return cast(str, list_env.dumps() + NoEscape("\n"))

    def _append_definition_list(self, doc: Document, tag: Tag) -> str:
        list_env: Environment = Environment()
        list_env._latex_name = "description"
        for _key, _value in zip(tag.find_all("dt"), tag.find_all("dd")):
            _tex_key: str = self._process_contents(doc=doc, contents=_key.contents)
            _command: str = Command("item", options=_tex_key).dumps()
            _tex_value: str = self._process_contents(doc=doc, contents=_value.contents)
            list_env.append(NoEscape(f"{_command} {_tex_value}"))
        return cast(str, list_env.dumps() + NoEscape("\n"))

    def _process_tag(self, doc: Document, tag: Tag) -> str:  # type: ignore

        match tag.name:

            case "a" if tag.has_attr("role") and "doc-noteref" in tag["role"]:
                return self._append_footnote(doc, tag)

            case "article" if tag.has_attr("class") and "epigraph" in tag["class"]:
                return self._append_epigraph(doc, tag)

            case "b":
                return self._append_bold(doc, tag)

            case "blockquote" if tag.has_attr("class") and "gatha" in tag["class"]:
                return self._append_verse(doc, tag)

            case "blockquote":
                return self._append_quotation(doc, tag)

            case "br":
                return self._append_breakline()

            case "cite":
                return self._append_italic(doc, tag)

            case "dl":
                return self._append_definition_list(doc, tag)

            case "em":
                return self._append_emphasis(doc, tag)

            case "h1":
                return self._append_chapter(tag)

            case "h2" if tag.has_attr("class") and "sutta-title" in tag["class"]:
                return self._append_section(tag)

            case "i" if tag.has_attr("lang") and any(_lang in tag["lang"] for _lang in ["pi", "san"]):
                return self._append_italic(doc, tag)

            case "i":
                return self._append_foreign_script_macro(doc, tag)

            case "ol" | "ul":
                return self._append_list(doc, tag)

            case "p":
                return self._append_paragraph(doc, tag)

            case "section" if tag.has_attr("id") and tag["id"] == "main-toc":
                return self._append_tableofcontents()

            case "span":
                return self._append_span(doc, tag)

            case _:
                return self._process_contents(doc=doc, contents=tag.contents)

    def _process_contents(self, doc: Document, contents: list[PageElement]) -> str:
        tex: str = ""

        for _element in contents:
            if isinstance(_element, Tag):
                tex += self._process_tag(doc=doc, tag=_element)
            elif isinstance(_element, NavigableString) and _element != "\n":
                tex += _element.replace("&", "\&")

        return cast(str, NoEscape(tex))

    @staticmethod
    def _process_template(volume: Volume, name: str) -> str:
        MATTERS_TO_TEMPLATES_NAMES_MAPPING: dict[str, str] = ast.literal_eval(
            os.getenv("MATTERS_TO_TEMPLATES_NAMES_MAPPING")  # type: ignore
        )
        if not MATTERS_TO_TEMPLATES_NAMES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable MATTERS_TO_TEMPLATES_NAMES_MAPPING."
            )
        else:
            try:
                _template_name: str = MATTERS_TO_TEMPLATES_NAMES_MAPPING[name].replace(".html", ".tex")
                _template_loader: FileSystemLoader = FileSystemLoader(searchpath=TEX_TEMPLATES_DIR)
                _template_env: jinja2_Environment = jinja2_Environment(loader=_template_loader, autoescape=True)
                _template: Template = _template_env.get_template(name=_template_name)
                tex: str = _template.render(**volume.dict())
                return tex

            except TemplateNotFound:
                log.warning(f"Matter '{name}' is not supported.")
                return ""

    @staticmethod
    def _get_matter_name(matter: Tag) -> str:
        name: str = matter["id"] if matter.has_attr("id") else matter["class"][0] if matter.has_attr("class") else ""
        return name

    def _process_html_element(self, volume: Volume, doc: Document, element: PageElement) -> str:
        if isinstance(element, Tag) and not (element.has_attr("id") and element["id"] in MATTERS_TO_SKIP):
            if (name := self._get_matter_name(element)) in MATTERS_WITH_TEX_TEMPLATES:
                return cast(str, NoEscape(self._process_template(volume=volume, name=name)))
            else:
                return cast(str, NoEscape(self._process_tag(doc=doc, tag=element)))
        elif isinstance(element, NavigableString) and element != "\n":
            return cast(str, element)
        else:
            return ""

    @staticmethod
    def _append_new_commands(doc: Document) -> None:
        _doc: str = doc.dumps()
        for _name, _command in NEW_COMMANDS.items():
            if f"\\{_name}" in _doc:
                doc.preamble.append(_command)

    @staticmethod
    def _append_packages(doc: Document) -> None:
        doc.packages.append(Package("epigraph"))
        doc.packages.append(Package("marginnote"))
        doc.packages.append(Package("setspace"))
        doc.packages.append(Package("soul"))

    def _generate_latex(self, volume: Volume) -> Document:
        # setup
        self.endnotes: list[str] | None = volume.endnotes if volume.endnotes else None

        doc = Document(documentclass="book")

        # set packages
        self._append_packages(doc)

        # set frontmatter
        doc.append(Command("frontmatter"))
        for _page in volume.frontmatter:
            _frontmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_frontmatter_element))

        # set mainmatter
        doc.append(Command("mainmatter"))
        _mainmatter: list[PageElement] = BeautifulSoup(volume.mainmatter, "lxml").find("body").contents
        for _mainmatter_element in _mainmatter:
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_mainmatter_element))

        # set backmatter
        doc.append(Command("backmatter"))
        for _page in volume.backmatter:
            _backmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_backmatter_element))

        # set new commands
        self._append_new_commands(doc)

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
