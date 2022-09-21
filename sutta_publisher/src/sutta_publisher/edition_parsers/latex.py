import ast
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable, cast

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from jinja2 import Environment as jinja2_Environment, FileSystemLoader, Template, TemplateNotFound
from pylatex import Description, Document, Enumerate, Itemize, NewPage, NoEscape
from pylatex.base_classes import Command, Environment
from pylatex.utils import bold, italic

from sutta_publisher.shared.value_objects.parser_objects import Volume

from .base import EditionParser
from .helper_functions import find_sutta_title_depth, get_heading_depth

log = logging.getLogger(__name__)

ADDITIONAL_PANNASAKA_IDS: list[str] = ast.literal_eval(os.getenv("ADDITIONAL_PANNASAKA_IDS", ""))
FOREIGN_SCRIPT_MACRO_LANGUAGES: list[str] = ast.literal_eval(os.getenv("FOREIGN_SCRIPT_MACRO_LANGUAGES", ""))
INDIVIDUAL_TEMPLATES_MAPPING: dict[str, list] = ast.literal_eval(os.getenv("INDIVIDUAL_TEMPLATES_MAPPING", ""))
LATEX_DOCUMENT_CONFIG: dict[str, str] = ast.literal_eval(os.getenv("LATEX_DOCUMENT_CONFIG", ""))
LATEX_TEMPLATES_MAPPING: dict[str, str] = ast.literal_eval(os.getenv("LATEX_TEMPLATES_MAPPING", ""))
MATTERS_TO_SKIP: list[str] = ast.literal_eval(os.getenv("MATTERS_TO_SKIP", ""))
MATTERS_WITH_TEX_TEMPLATES: list[str] = ast.literal_eval(os.getenv("MATTERS_WITH_TEX_TEMPLATES", ""))
SANSKRIT_LANGUAGES: list[str] = ast.literal_eval(os.getenv("SANSKRIT_LANGUAGES", ""))
SANSKRIT_PATTERN = re.compile(r"\b(?=\w*[āīūṭḍṁṅñṇḷśṣṛ])\w+\b")
STYLING_CLASSES: list[str] = ast.literal_eval(os.getenv("STYLING_CLASSES", ""))
SUTTATITLES_WITHOUT_TRANSLATED_TITLE: list[str] = ast.literal_eval(
    os.getenv("SUTTATITLES_WITHOUT_TRANSLATED_TITLE", "")
)
TEXTS_WITH_CHAPTER_SUTTA_TITLES: dict[str, str | tuple] = ast.literal_eval(
    os.getenv("TEXTS_WITH_CHAPTER_SUTTA_TITLES", "")
)


class LatexEdition(EditionParser):
    TEX_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "tex"
    IMGAGES_DIR = Path(__file__).parent.parent / "images"
    edition_type = "latex_parser"
    endnotes: list[str] | None
    section_type: str
    sutta_depth: int

    @staticmethod
    def _is_styled(tag: Tag) -> bool:
        if tag.has_attr("class"):
            return any(_class in STYLING_CLASSES for _class in tag["class"])
        else:
            return False

    @staticmethod
    def _apply_styling(tag: Tag, tex: str) -> str:
        for _class in tag["class"]:
            if _class in STYLING_CLASSES:
                return cast(str, Command(f'sc{_class.replace("-", "")}', NoEscape(tex)).dumps())
        return tex

    @staticmethod
    def _append_marginnote(tex: str, uid: str) -> str:
        """Add marginnote before first space"""
        marginnote = Command("marginnote", uid).dumps()
        try:
            tex_1, tex_2 = tex.split(" ", 1)
        except ValueError:
            return f"{tex}{marginnote} "
        return f"{tex_1}{marginnote} {tex_2}"

    def _append_p(self, doc: Document, tag: Tag) -> str:
        tex: str = self._process_contents(doc=doc, contents=tag.contents)

        if LatexEdition._is_styled(tag=tag):
            tex = LatexEdition._apply_styling(tag=tag, tex=tex)
        elif tag.has_attr("id"):
            if self.config.edition.text_uid == "dhp":
                # Dhammapada only marginnote uid
                _uid: str = tag["id"].split(":")[0][3:]
            else:
                # default marginnote uid
                _uid = tag["id"].split(":")[1]

            tex = LatexEdition._append_marginnote(tex=tex, uid=_uid)

        return cast(str, tex + NoEscape("\n\n"))

    def _append_span(self, doc: Document, tag: Tag) -> str:
        if tag.has_attr("class"):
            if all(_class in tag["class"] for _class in ["blurb-item", "root-title"]):
                return f"({self._append_italic(doc=doc, tag=tag)})"
            else:
                tex: str = self._process_contents(doc=doc, contents=tag.contents)

                if all(_class in tag["class"] for _class in ["blurb-item", "acronym"]):
                    return f"{tex}: "

                tex = LatexEdition._apply_styling(tag=tag, tex=tex)
                return tex
        else:
            return self._process_contents(doc=doc, contents=tag.contents)

    def _append_verse(self, doc: Document, tag: Tag) -> str:
        verse_env: Environment = Environment()
        verse_env._latex_name = "verse"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        verse_env.append(_data)
        return cast(str, verse_env.dumps() + NoEscape("\n\n"))

    def _append_quotation(self, doc: Document, tag: Tag) -> str:
        quotation_env: Environment = Environment()
        quotation_env._latex_name = "quotation"
        _data: str = self._process_contents(doc=doc, contents=tag.contents)
        quotation_env.append(_data)
        return cast(str, quotation_env.dumps() + NoEscape("\n\n"))

    @staticmethod
    def _append_breakline() -> str:
        return cast(str, NoEscape(r"\\") + NoEscape("\n"))

    def _append_bold(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, bold(_tex, escape=False))

    def _append_emphasis(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, Command("emph", _tex).dumps())

    @staticmethod
    def _append_sanskrit(tex: str) -> str:
        return cast(str, Command("textsanskrit", tex).dumps())

    def _append_italic(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        if (
            tag.has_attr("class")
            and "\\textsanskrit" not in _tex
            and (
                any(_class in SANSKRIT_LANGUAGES for _class in tag["class"])
                or all(_class in ["blurb-item", "root-title"] for _class in tag["class"])
            )
        ):
            _tex = LatexEdition._append_sanskrit(_tex)
        return cast(str, italic(_tex, escape=False))

    def _append_foreign_script_macro(self, doc: Document, tag: Tag) -> str:
        _tex: str = self._process_contents(doc=doc, contents=tag.contents)
        return cast(str, Command(f'lang{tag["lang"]}', _tex).dumps())

    def _append_footnote(self, doc: Document) -> str:
        if self.endnotes:
            _endnote = BeautifulSoup(self.endnotes.pop(0), "lxml")
            _contents = _endnote.p.contents if _endnote.p else _endnote.body.contents
            _data: str = self._process_contents(doc=doc, contents=_contents)
            return cast(str, Command("footnote", _data).dumps())
        else:
            return ""

    def _append_sutta_title(self, doc: Document, tag: Tag) -> str:
        tex: str = ""
        _acronym, _name, _root_name = [self._process_tag(doc=doc, tag=_span) for _span in tag.children]
        template: Template = LatexEdition._get_template(name="heading")
        data = {
            "acronym": _acronym,
            "name": _name,
            "root_name": _root_name,
            "section_type": self.section_type,
            "display_name": tag.parent and tag.parent.get("id") not in SUTTATITLES_WITHOUT_TRANSLATED_TITLE,
        }
        tex += template.render(data) + NoEscape("\n\n")
        return cast(str, tex)

    @staticmethod
    def _append_custom_chapter(doc: Document, tag: Tag) -> str:
        _template: Template = LatexEdition._get_template(name="chapter")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_custom_section(self, doc: Document, tag: Tag) -> str:
        tex: str = ""
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex += Command("section*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "section", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n\n")
        return tex

    @staticmethod
    def _append_custom_part(doc: Document, tag: Tag) -> str:
        _template: Template = LatexEdition._get_template(name="part")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_chapter(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("chapter*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "chapter", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n\n")
        return tex

    def _append_section(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("section*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subsection(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("subsection*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subsubsection(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("subsubsection*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_paragraph(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("paragraph*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subparagraph(self, doc: Document, tag: Tag) -> str:
        _title: str = self._process_contents(doc=doc, contents=tag.contents)
        tex: str = Command("subparagraph*", _title).dumps() + NoEscape("\n\n")
        return tex

    @staticmethod
    def _append_pannasa(tag: Tag) -> str:
        _template: Template = LatexEdition._get_template(name="pannasa")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_section_title(self, doc: Document, tag: Tag) -> str:
        if tag.has_attr("id") and ("pannasaka" in tag["id"] or tag["id"] in ADDITIONAL_PANNASAKA_IDS):
            # The pannasa in AN and SN requires a special markup
            return LatexEdition._append_pannasa(tag=tag)

        else:
            actions: list[Callable] = [
                LatexEdition._append_custom_part,
                LatexEdition._append_custom_chapter,
            ]
            _heading_depth: int = get_heading_depth(tag)

            # Samyutta only - move all headings one level up in order to remove the top level heading
            if self.config.edition.text_uid == "sn":
                _heading_depth -= 1
                if not _heading_depth:
                    return ""

            if self.sutta_depth == 2:
                index = _heading_depth
            elif _heading_depth in (1, 2):
                index = _heading_depth - 1
            else:
                index = -1
            return cast(str, actions[index](doc=doc, tag=tag))

    def _append_subheading(self, doc: Document, tag: Tag) -> str:
        actions: list[Callable] = [
            self._append_subsection,
            self._append_subsubsection,
            self._append_paragraph,
            self._append_subparagraph,
        ]
        if self.section_type == "chapter":
            actions.insert(0, self._append_section)

        index = int(tag.name[1]) - self.sutta_depth - 1
        return cast(str, actions[index](doc=doc, tag=tag))

    @staticmethod
    def _append_tableofcontents() -> str:
        tex = Command("tableofcontents").dumps() + NoEscape("\n")
        tex += NewPage().dumps() + NoEscape("\n")
        tex += Command("pagestyle", "fancy").dumps() + NoEscape("\n")
        return cast(str, tex)

    def _append_epigraph(self, doc: Document, tag: Tag) -> str:
        data: dict[str, str] = {}
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
                LatexEdition._strip_tag_string(_tag)
                data[_var] = self._process_contents(doc=doc, contents=_tag.contents)

        template: Template = LatexEdition._get_template(name="epigraph")
        return cast(str, template.render(data) + NoEscape("\n"))

    def _append_enjambment(self, doc: Document, tag: Tag) -> str:
        return cast(str, f"\\\\>{self._process_contents(doc=doc, contents=tag.contents)}")

    def _append_enumerate(self, doc: Document, tag: Tag) -> str:
        enum = Enumerate()
        for _item in tag.contents:
            if isinstance(_item, Tag):
                enum.add_item(s=self._process_tag(doc=doc, tag=_item))
        return cast(str, enum.dumps().replace("\\item%\n", "\\item ") + NoEscape("\n\n"))

    def _append_itemize(self, doc: Document, tag: Tag) -> str:
        itemize = Itemize()
        for _item in tag.contents:
            if isinstance(_item, Tag):
                itemize.add_item(s=self._process_tag(doc=doc, tag=_item))
        return cast(str, itemize.dumps().replace("\\item%\n", "\\item ") + NoEscape("\n\n"))

    def _append_description(self, doc: Document, tag: Tag) -> str:
        desc = Description()
        for _key, _value in zip(tag.find_all("dt"), tag.find_all("dd")):
            _label = self._process_contents(doc=doc, contents=_key.contents)
            _item = self._process_contents(doc=doc, contents=_value.contents)
            desc.add_item(label=_label, s=_item)
        tex = desc.dumps().replace("]%\n", "] ")

        return cast(str, tex + NoEscape("\n\n"))

    def _append_heading(self, doc: Document, tag: Tag) -> str:
        actions: list[Callable] = [
            self._append_chapter,
            self._append_section,
            self._append_subsection,
            self._append_subsubsection,
            self._append_paragraph,
            self._append_subparagraph,
        ]
        _depth: int = get_heading_depth(tag)
        return cast(str, actions[_depth - 1](doc=doc, tag=tag))

    def _is_range_or_sutta_title(self, tag: Tag) -> bool:
        return (
            tag.has_attr("class")
            and "heading" in tag["class"]
            and any(_class in tag["class"] for _class in ["sutta-title", "range-title"])
            and int(tag.name[1:]) == self.sutta_depth
        )

    def _process_tag(self, doc: Document, tag: Tag) -> str:

        match tag.name:

            case range_or_sutta_title if self._is_range_or_sutta_title(tag=tag):
                return self._append_sutta_title(doc=doc, tag=tag)

            case section_title if tag.has_attr("class") and "section-title" in tag["class"]:
                return self._append_section_title(doc=doc, tag=tag)

            case subheading if tag.has_attr("class") and "subheading" in tag["class"]:
                return self._append_subheading(doc=doc, tag=tag)

            case heading if tag.name.startswith("h") and tag.name[1].isnumeric():
                return self._append_heading(doc=doc, tag=tag)

            case macro_lang if tag.has_attr("lang") and tag["lang"] in FOREIGN_SCRIPT_MACRO_LANGUAGES:
                return self._append_foreign_script_macro(doc=doc, tag=tag)

            case "a" if tag.has_attr("role") and "doc-noteref" in tag["role"]:
                return self._append_footnote(doc=doc)

            case "article" if tag.has_attr("class") and "epigraph" in tag["class"]:
                return self._append_epigraph(doc=doc, tag=tag)

            case "b":
                return self._append_bold(doc=doc, tag=tag)

            case "blockquote" if tag.has_attr("class") and "gatha" in tag["class"]:
                return self._append_verse(doc=doc, tag=tag)

            case "blockquote":
                return self._append_quotation(doc=doc, tag=tag)

            case "br":
                return LatexEdition._append_breakline()

            case "cite":
                return self._append_italic(doc=doc, tag=tag)

            case "dl":
                return self._append_description(doc=doc, tag=tag)

            case "em":
                return self._append_emphasis(doc=doc, tag=tag)

            case "i" if tag.has_attr("lang"):
                return self._append_italic(doc=doc, tag=tag)

            case "i":
                return self._append_italic(doc=doc, tag=tag)

            case "j":
                return self._append_enjambment(doc=doc, tag=tag)

            case "ol":
                return self._append_enumerate(doc=doc, tag=tag)

            case "p":
                return self._append_p(doc=doc, tag=tag)

            case "section" if tag.has_attr("id") and tag["id"] == "main-toc":
                return LatexEdition._append_tableofcontents()

            case "section" if tag.has_attr("class") and "secondary-toc" in tag["class"]:
                return ""

            case "span":
                return self._append_span(doc=doc, tag=tag)

            case "ul":
                return self._append_itemize(doc=doc, tag=tag)

        return self._process_contents(doc=doc, contents=tag.contents)

    def _process_contents(self, doc: Document, contents: list[PageElement]) -> str:
        tex: str = ""

        for _element in contents:
            if isinstance(_element, Tag):
                tex += self._process_tag(doc=doc, tag=_element)
            elif isinstance(_element, NavigableString) and _element != "\n":
                if not (_element.parent.has_attr("class") and "sutta-heading" in _element.parent["class"]):
                    _element = re.sub(SANSKRIT_PATTERN, r"\\textsanskrit{\g<0>}", _element)
                tex += _element.replace("&", "\\&").replace("_", "\\_").replace("~", "\\textasciitilde")

        return cast(str, NoEscape(tex))

    @staticmethod
    def _strip_tag_string(tag: Tag) -> None:
        for _element in tag:
            if isinstance(_element, NavigableString):
                _element.string.replace_with(_element.string.strip())

    @staticmethod
    def _get_template(name: str = "", is_shared: bool = True) -> Template:
        if is_shared:
            if not LATEX_TEMPLATES_MAPPING:
                raise EnvironmentError(
                    "Missing .env_public file or the file lacks required variable LATEX_TEMPLATES_MAPPING."
                )
            try:
                _template_name: str = LATEX_TEMPLATES_MAPPING[name]
            except KeyError:
                raise EnvironmentError(
                    f"'LATEX_TEMPLATES_MAPPING' in .env_public file lacks required key-value pair for {name} template."
                )
            _subdir = "shared"

        else:
            _template_name = name
            _subdir = "individual"

        try:
            _template_loader: FileSystemLoader = FileSystemLoader(searchpath=LatexEdition.TEX_TEMPLATES_DIR / _subdir)
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
            raise TemplateNotFound(f"Template '{_template_name}' for Latex edition is missing.")

    @staticmethod
    def _get_matter_name(matter: Tag) -> str:
        name: str = matter["id"] if matter.has_attr("id") else matter["class"][0] if matter.has_attr("class") else ""
        return name

    def _process_html_element(self, volume: Volume, doc: Document, element: PageElement) -> str:
        if isinstance(element, Tag) and not (element.has_attr("id") and element["id"] in MATTERS_TO_SKIP):
            if (name := LatexEdition._get_matter_name(element)) in MATTERS_WITH_TEX_TEMPLATES:
                _template: Template = LatexEdition._get_template(name=name)
                tex = _template.render(
                    **volume.dict(exclude_none=True, exclude_unset=True), images_directory=LatexEdition.IMGAGES_DIR
                )
                return cast(str, NoEscape(tex))
            else:
                return cast(str, NoEscape(self._process_tag(doc=doc, tag=element)))
        elif isinstance(element, NavigableString) and element != "\n":
            return cast(str, element)
        else:
            return ""

    @staticmethod
    def _remove_all_nav(html: PageElement) -> None:
        any(_tag.decompose() for _tag in html.find_all("nav"))

    def _has_chapter_sutta_title(self, volume: Volume) -> bool:
        if value := TEXTS_WITH_CHAPTER_SUTTA_TITLES.get(self.config.edition.text_uid):
            return value == "all" or volume.volume_number in value
        return False

    def _prepare_mainmatter(self, volume: Volume, doc: Document, html: BeautifulSoup) -> None:
        self.sutta_depth = find_sutta_title_depth(html)

        if self.sutta_depth <= 2:  # append additional latex part heading
            _tag = html.new_tag("h1")
            _title = (
                volume.volume_translation_title
                if volume.volume_translation_title
                else self.config.publication.translation_title
            )
            _tag.string = _title
            doc.append(NoEscape(LatexEdition._append_custom_part(doc=doc, tag=_tag)))

    def _append_individual_config(self, doc: Document, volume: Volume) -> None:
        try:
            _edition_mapping = INDIVIDUAL_TEMPLATES_MAPPING.get(self.config.edition.text_uid)
        except KeyError:
            raise EnvironmentError(f"Individual template mapping for {self.config.edition.text_uid} not found.")

        if isinstance(_edition_mapping, list):
            _template_name = _edition_mapping[volume.volume_number - 1]
        else:
            _template_name = _edition_mapping

        try:
            _template: Template = LatexEdition._get_template(name=_template_name, is_shared=False)
            doc.preamble.append(NoEscape(_template.render()))
        except TemplateNotFound:
            log.info(f"Template '{_template_name}' for edition specific configuration not found.")

    def _append_preamble(self, doc: Document, volume: Volume) -> None:
        _template: Template = LatexEdition._get_template(name="preamble")
        doc.preamble.append(NoEscape(_template.render()))
        self._append_individual_config(doc=doc, volume=volume)

    @staticmethod
    def _set_xmpdata(volume: Volume) -> None:
        _template: Template = LatexEdition._get_template(name="metadata")
        _output = _template.render(**volume.dict(exclude_none=True, exclude_unset=True))
        _path = Path(tempfile.gettempdir()) / f"{volume.filename}.xmpdata"

        with open(file=_path, mode="wt") as f:
            f.write(_output)

    def _generate_latex(self, volume: Volume) -> Document:
        # setup
        self.endnotes: list[str] | None = volume.endnotes if volume.endnotes else None
        self.section_type: str = "chapter" if self._has_chapter_sutta_title(volume=volume) else "section"

        # create .xmpdata file
        LatexEdition._set_xmpdata(volume=volume)

        doc = Document(**LATEX_DOCUMENT_CONFIG)

        # set preamble
        self._append_preamble(doc=doc, volume=volume)

        # set frontmatter
        doc.append(Command("frontmatter"))
        for _page in volume.frontmatter:
            _frontmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            LatexEdition._remove_all_nav(html=_frontmatter_element)
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_frontmatter_element))

        # set mainmatter
        doc.append(Command("mainmatter"))
        doc.append(Command("pagestyle", "fancy"))
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        self._prepare_mainmatter(volume=volume, doc=doc, html=_mainmatter)

        _mainmatter_elements = _mainmatter.find("body").contents
        for _element in _mainmatter_elements:
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_element))

        # set backmatter
        doc.append(Command("backmatter"))
        for _page in volume.backmatter:
            _backmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, doc=doc, element=_backmatter_element))

        return doc
