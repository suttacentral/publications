import ast
import logging
import os.path
from pathlib import Path
from typing import cast

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from jinja2 import Environment as jinja2_Environment, FileSystemLoader, Template, TemplateNotFound
from pylatex import Document, NoEscape
from pylatex.base_classes import Command, Environment
from pylatex.utils import bold, italic

from sutta_publisher.shared.value_objects.parser_objects import Volume

from .base import EditionParser

log = logging.getLogger(__name__)

MATTERS_TO_SKIP: list[str] = [
    "endnotes",
]
MATTERS_WITH_TEX_TEMPLATES: list[str] = [
    "titlepage",
    "imprint",
    "halftitlepage",
]
STYLING_CLASSES: list[str] = [
    "namo",
    "endsection",
    "endsutta",
    "endbook",
    "endkanda",
    "end",
    "uddana-intro",
    "endvagga",
    "rule",
    "add",
    "evam",
    "speaker",
]
TEX_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "tex"


class LatexEdition(EditionParser):
    edition_type = "latex_parser"
    endnotes: list[str] | None

    def _append_paragraph(self, doc: Document, tag: Tag) -> str:
        tex: str = ""

        if tag.has_attr("id"):
            tex += Command("marginnote", tag["id"].split(":")[1], tag["id"].split(":")[1]).dumps()

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

    def _append_section(self, tag: Tag) -> str:
        _acronym, _name, _root_name = tag.stripped_strings
        _template: Template = self._get_template("heading")
        return _template.render(acronym=_acronym, name=_name, root_name=_root_name)

    def _append_chapter(self, doc: Document, tag: Tag) -> str:
        tex: str = ""
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex += Command("chapter*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "chapter", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n")
        return tex

    def _append_part(self, tag: Tag) -> str:
        _name = tag.string
        _template: Template = self._get_template("part")
        return _template.render(name=_name)

    @staticmethod
    def _append_tableofcontents() -> str:
        return cast(str, Command("tableofcontents").dumps())

    def _append_epigraph(self, doc: Document, tag: Tag) -> str:
        _data: dict[str, str] = {}
        _epigraph_classes: dict[str, str] = {
            "text": "epigraph-text",
            "translated_title": "epigraph-translated-title",
            "root_title": "epigraph-root-title",
            "reference": "epigraph-reference",
        }

        for _var, _class in _epigraph_classes.items():
            if _tag := tag.find(class_=_class):
                if _class == "epigraph-text":
                    _tag = _tag.p
                self._strip_tag_string(_tag)
                _data[_var] = self._process_contents(doc=doc, contents=_tag.contents)

        _template: Template = self._get_template(name="epigraph")
        return _template.render(_data)

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

            case section if tag.has_attr("class") and any(
                _class in tag["class"] for _class in ["sutta-title", "range-title"]
            ):
                return self._append_section(tag)

            case part if tag.name == "h1" and tag.has_attr("class") and "section-title" in tag["class"]:
                return self._append_part(tag)

            case chapter if tag.name == "h2" and tag.has_attr("class") and "section-title" in tag["class"]:
                return self._append_chapter(doc, tag)

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
                return self._append_chapter(doc, tag)

            case "i" if tag.has_attr("lang") and any(_lang in tag["lang"] for _lang in ["pi", "sa"]):
                return self._append_italic(doc, tag)

            case "i" if tag.has_attr("lang"):
                return self._append_foreign_script_macro(doc, tag)

            case "i":
                return self._append_italic(doc, tag)

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
    def _strip_tag_string(tag: Tag) -> None:
        for _element in tag:
            if isinstance(_element, NavigableString):
                _element.string.replace_with(_element.string.strip())

    @staticmethod
    def _get_template(name: str) -> Template:
        LATEX_TEMPLATES_NAMES_MAPPING: dict[str, str] = ast.literal_eval(
            os.getenv("LATEX_TEMPLATES_NAMES_MAPPING")  # type: ignore
        )
        if not LATEX_TEMPLATES_NAMES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable LATEX_TEMPLATES_NAMES_MAPPING."
            )
        else:
            try:
                _template_name: str = LATEX_TEMPLATES_NAMES_MAPPING[name]
                _template_loader: FileSystemLoader = FileSystemLoader(searchpath=TEX_TEMPLATES_DIR)
                _template_env: jinja2_Environment = jinja2_Environment(
                    block_start_string="\BLOCK{",
                    block_end_string="}",
                    variable_start_string="\VAR{",
                    variable_end_string="}",
                    comment_start_string="\#{",
                    comment_end_string="}",
                    line_statement_prefix="%%",
                    line_comment_prefix="%#",
                    trim_blocks=True,
                    autoescape=True,
                    loader=_template_loader,
                )
                template: Template = _template_env.get_template(name=_template_name)
                return template

            except TemplateNotFound:
                raise TemplateNotFound(f"Template '{name}-template.tex' for Latex edition is missing.")

    @staticmethod
    def _get_matter_name(matter: Tag) -> str:
        name: str = matter["id"] if matter.has_attr("id") else matter["class"][0] if matter.has_attr("class") else ""
        return name

    def _process_html_element(self, volume: Volume, doc: Document, element: PageElement) -> str:
        if isinstance(element, Tag) and not (element.has_attr("id") and element["id"] in MATTERS_TO_SKIP):
            if (name := self._get_matter_name(element)) in MATTERS_WITH_TEX_TEMPLATES:
                _template: Template = self._get_template(name=name)
                return cast(str, NoEscape(_template.render(**volume.dict())))
            else:
                return cast(str, NoEscape(self._process_tag(doc=doc, tag=element)))
        elif isinstance(element, NavigableString) and element != "\n":
            return cast(str, element)
        else:
            return ""

    def _append_preamble(self, doc: Document) -> None:
        _template: Template = self._get_template(name="preamble")
        doc.preamble.append(NoEscape(_template.render()))

    def _generate_latex(self, volume: Volume) -> Document:
        # setup
        self.endnotes: list[str] | None = volume.endnotes if volume.endnotes else None

        doc = Document(documentclass="book", document_options="12pt")

        # set preamble
        self._append_preamble(doc)

        # set frontmatter
        doc.append(Command("frontmatter"))
        for _page in volume.frontmatter:
            _frontmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_frontmatter_element))

        # set mainmatter
        doc.append(Command("mainmatter"))
        doc.append(Command("pagestyle", "fancy"))
        _mainmatter: list[PageElement] = BeautifulSoup(volume.mainmatter, "lxml").find("body").contents
        for _mainmatter_element in _mainmatter:
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_mainmatter_element))

        # set backmatter
        doc.append(Command("backmatter"))
        for _page in volume.backmatter:
            _backmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_backmatter_element))

        return doc
