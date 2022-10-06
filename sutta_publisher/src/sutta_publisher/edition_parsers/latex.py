import ast
import logging
import os
import re
from copy import copy
from pathlib import Path
from typing import Any, Callable, cast, no_type_check

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from jinja2 import Environment as jinja2_Environment, FileSystemLoader, Template, TemplateNotFound
from pylatex import Description, Document, Enumerate, Itemize, NewPage, NoEscape
from pylatex.base_classes import Command, Environment
from pylatex.utils import bold, italic

from sutta_publisher.shared.value_objects.parser_objects import Volume

from .base import EditionParser
from .helper_functions import find_sutta_title_depth, get_heading_depth, get_individual_cover_template_name, wrap_in_z

log = logging.getLogger(__name__)

ADDITIONAL_PANNASAKA_IDS: list[str] = ast.literal_eval(os.getenv("ADDITIONAL_PANNASAKA_IDS", ""))
COVER_TEMPLATES_MAPPING: dict[str, str] = ast.literal_eval(os.getenv("COVER_TEMPLATES_MAPPING", ""))
FOREIGN_SCRIPT_MACRO_LANGUAGES: list[str] = ast.literal_eval(os.getenv("FOREIGN_SCRIPT_MACRO_LANGUAGES", ""))
INDIVIDUAL_TEMPLATES_MAPPING: dict[str, list] = ast.literal_eval(os.getenv("INDIVIDUAL_TEMPLATES_MAPPING", ""))
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


class CustomEnumerate(Enumerate):
    _latex_name = "enumerate"

    def add_item(self, s: str, options: str | list[str] | None = None) -> None:
        """Overwrite the default method in order to support additional options for list items"""
        self.append(Command("item", options=options))
        self.append(s)


class LatexParser(EditionParser):
    edition_type = "latex_parser"

    LATEX_DOCUMENT_CONFIG: dict[str, str | tuple[str]] = ast.literal_eval(os.getenv("LATEX_DOCUMENT_CONFIG", ""))
    LATEX_COVER_CONFIG: dict[str, str | tuple[str]] = ast.literal_eval(os.getenv("LATEX_COVER_CONFIG", ""))

    IMAGES_DIR = os.path.join(Path(__file__).parent.parent / "images", "")  # os.path.join -> add a trailing slash
    TEX_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "tex"
    INDIVIDUAL_TEMPLATES_SUBDIR = "individual"
    SHARED_TEMPLATES_SUBDIR = "shared"
    COVER_TEMPLATES_SUBDIR = "cover"

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

    def _append_p(self, tag: Tag) -> str:
        tex: str = self._process_contents(contents=tag.contents)

        if LatexParser._is_styled(tag=tag):
            tex = LatexParser._apply_styling(tag=tag, tex=tex)
        elif tag.has_attr("id"):
            if self.config.edition.text_uid == "dhp":
                # Dhammapada only marginnote uid
                _uid: str = tag["id"].split(":")[0][3:]
            else:
                # default marginnote uid
                _uid = tag["id"].split(":")[1]

            tex = LatexParser._append_marginnote(tex=tex, uid=_uid)

        return cast(str, tex + NoEscape("\n\n"))

    def _append_span(self, tag: Tag) -> str:
        if tag.has_attr("class"):
            if all(_class in tag["class"] for _class in ["blurb-item", "root-title"]):
                return f"({self._append_italic(tag=tag)})"
            else:
                tex: str = self._process_contents(contents=tag.contents)

                if all(_class in tag["class"] for _class in ["blurb-item", "acronym"]):
                    return f"{tex}: "

                tex = LatexParser._apply_styling(tag=tag, tex=tex)
                return tex
        else:
            return self._process_contents(contents=tag.contents)

    def _append_verse(self, tag: Tag) -> str:
        verse_env: Environment = Environment()
        verse_env._latex_name = "verse"
        _data: str = self._process_contents(contents=tag.contents)
        verse_env.append(_data)
        return cast(str, verse_env.dumps() + NoEscape("\n\n"))

    def _append_quotation(self, tag: Tag) -> str:
        quotation_env: Environment = Environment()
        quotation_env._latex_name = "quotation"
        _data: str = self._process_contents(contents=tag.contents)
        quotation_env.append(_data)
        return cast(str, quotation_env.dumps() + NoEscape("\n\n"))

    @staticmethod
    def _append_breakline() -> str:
        return cast(str, NoEscape(r"\\") + NoEscape("\n"))

    def _append_bold(self, tag: Tag) -> str:
        _tex: str = self._process_contents(contents=tag.contents)
        return cast(str, bold(_tex, escape=False))

    def _append_emphasis(self, tag: Tag) -> str:
        _tex: str = self._process_contents(contents=tag.contents)
        return cast(str, Command("emph", _tex).dumps())

    @staticmethod
    def _append_thematic_break() -> str:
        return cast(str, Command("thematicbreak").dumps() + NoEscape("\n"))

    @staticmethod
    def _append_sanskrit(tex: str) -> str:
        return cast(str, Command("textsanskrit", tex).dumps())

    def _append_italic(self, tag: Tag) -> str:
        _tex: str = self._process_contents(contents=tag.contents)
        if (
            tag.has_attr("class")
            and "\\textsanskrit" not in _tex
            and (
                any(_class in SANSKRIT_LANGUAGES for _class in tag["class"])
                or all(_class in ["blurb-item", "root-title"] for _class in tag["class"])
            )
        ):
            _tex = LatexParser._append_sanskrit(_tex)
        return cast(str, italic(_tex, escape=False))

    def _append_foreign_script_macro(self, tag: Tag) -> str:
        _tex: str = self._process_contents(contents=tag.contents)
        return cast(str, Command(f'lang{tag["lang"]}', _tex).dumps())

    def _append_footnote(self) -> str:
        if self.endnotes:
            _endnote = BeautifulSoup(self.endnotes.pop(0), "lxml")
            _contents = _endnote.p.contents if _endnote.p else _endnote.body.contents
            _data: str = self._process_contents(contents=_contents)
            return cast(str, Command("footnote", _data).dumps())
        else:
            return ""

    def _append_sutta_title(self, tag: Tag) -> str:
        tex: str = ""
        _acronym, _name, _root_name = [self._process_tag(tag=_span) for _span in tag.children]
        template: Template = LatexParser._get_shared_template(name="heading")
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
    def _append_custom_chapter(tag: Tag) -> str:
        _template: Template = LatexParser._get_shared_template(name="chapter")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_custom_section(self, tag: Tag) -> str:
        tex: str = ""
        _title: str = self._process_contents(contents=tag.contents)
        tex += Command("section*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "section", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n\n")
        return tex

    @staticmethod
    def _append_custom_part(tag: Tag) -> str:
        _template: Template = LatexParser._get_shared_template(name="part")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_chapter(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("chapter*", _title).dumps() + NoEscape("\n")
        tex += Command("addcontentsline", arguments=["toc", "chapter", _title]).dumps() + NoEscape("\n")
        tex += Command("markboth", arguments=[_title, _title]).dumps() + NoEscape("\n\n")
        return tex

    def _append_section(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("section*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subsection(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("subsection*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subsubsection(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("subsubsection*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_paragraph(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("paragraph*", _title).dumps() + NoEscape("\n\n")
        return tex

    def _append_subparagraph(self, tag: Tag) -> str:
        _title: str = self._process_contents(contents=tag.contents)
        tex: str = Command("subparagraph*", _title).dumps() + NoEscape("\n\n")
        return tex

    @staticmethod
    def _append_pannasa(tag: Tag) -> str:
        _template: Template = LatexParser._get_shared_template(name="pannasa")
        return cast(str, _template.render(name=tag.string) + NoEscape("\n\n"))

    def _append_section_title(self, tag: Tag) -> str:
        if tag.has_attr("id") and ("pannasaka" in tag["id"] or tag["id"] in ADDITIONAL_PANNASAKA_IDS):
            # The pannasa in AN and SN requires a special markup
            return LatexParser._append_pannasa(tag=tag)
        elif self.section_type == "chapter":
            return cast(str, LatexParser._append_custom_part(tag=tag))
        else:
            actions: list[Callable] = [
                LatexParser._append_custom_part,
                LatexParser._append_custom_chapter,
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

            return cast(str, actions[index](tag=tag))

    def _append_subheading(self, tag: Tag) -> str:
        actions: list[Callable] = [
            self._append_subsection,
            self._append_subsubsection,
            self._append_paragraph,
            self._append_subparagraph,
        ]
        if self.section_type == "chapter":
            actions.insert(0, self._append_section)

        index = int(tag.name[1]) - self.sutta_depth - 1
        return cast(str, actions[index](tag=tag))

    @staticmethod
    def _append_tableofcontents() -> str:
        tex = Command("tableofcontents").dumps() + NoEscape("\n")
        tex += NewPage().dumps() + NoEscape("\n")
        tex += Command("pagestyle", "fancy").dumps() + NoEscape("\n")
        return cast(str, tex)

    def _append_epigraph(self, tag: Tag) -> str:
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
                LatexParser._strip_tag_string(_tag)
                data[_var] = self._process_contents(contents=_tag.contents)

        template: Template = LatexParser._get_shared_template(name="epigraph")
        return cast(str, template.render(data) + NoEscape("\n"))

    def _append_enjambment(self, tag: Tag) -> str:
        return cast(str, f"\\\\>{self._process_contents(contents=tag.contents)}")

    def _append_enumerate(self, tag: Tag) -> str:
        enum = CustomEnumerate()
        for _item in tag.contents:
            if isinstance(_item, Tag):
                if _li_value := _item.get("value"):
                    enum.add_item(s=self._process_tag(tag=_item), options=f"{_li_value}.")
                else:
                    enum.add_item(s=self._process_tag(tag=_item))
        return cast(str, enum.dumps().replace("\\item%\n", "\\item ").replace("]%\n", "] ") + NoEscape("\n\n"))

    def _append_itemize(self, tag: Tag) -> str:
        itemize = Itemize()
        for _item in tag.contents:
            if isinstance(_item, Tag):
                itemize.add_item(s=self._process_tag(tag=_item))
        return cast(str, itemize.dumps().replace("\\item%\n", "\\item ") + NoEscape("\n\n"))

    def _append_description(self, tag: Tag) -> str:
        desc = Description()
        for _key, _value in zip(tag.find_all("dt"), tag.find_all("dd")):
            _label = self._process_contents(contents=_key.contents)
            _item = self._process_contents(contents=_value.contents)
            desc.add_item(label=_label, s=_item)
        tex = desc.dumps().replace("]%\n", "] ")

        return cast(str, tex + NoEscape("\n\n"))

    def _append_heading(self, tag: Tag) -> str:
        actions: list[Callable] = [
            self._append_chapter,
            self._append_section,
            self._append_subsection,
            self._append_subsubsection,
            self._append_paragraph,
            self._append_subparagraph,
        ]
        _depth: int = get_heading_depth(tag)
        return cast(str, actions[_depth - 1](tag=tag))

    def _is_range_or_sutta_title(self, tag: Tag) -> bool:
        return (
            tag.has_attr("class")
            and "heading" in tag["class"]
            and any(_class in tag["class"] for _class in ["sutta-title", "range-title"])
            and int(tag.name[1:]) == self.sutta_depth
        )

    def _process_tag(self, tag: Tag | PageElement) -> str:

        match tag.name:

            case range_or_sutta_title if self._is_range_or_sutta_title(tag=tag):
                return self._append_sutta_title(tag=tag)

            case section_title if tag.has_attr("class") and "section-title" in tag["class"]:
                return self._append_section_title(tag=tag)

            case subheading if tag.has_attr("class") and "subheading" in tag["class"]:
                return self._append_subheading(tag=tag)

            case heading if tag.name.startswith("h") and tag.name[1].isnumeric():
                return self._append_heading(tag=tag)

            case macro_lang if tag.has_attr("lang") and tag["lang"] in FOREIGN_SCRIPT_MACRO_LANGUAGES:
                return self._append_foreign_script_macro(tag=tag)

            case "a" if tag.has_attr("role") and "doc-noteref" in tag["role"]:
                return self._append_footnote()

            case "article" if tag.has_attr("class") and "epigraph" in tag["class"]:
                return self._append_epigraph(tag=tag)

            case "b":
                return self._append_bold(tag=tag)

            case "blockquote" if tag.has_attr("class") and "gatha" in tag["class"]:
                return self._append_verse(tag=tag)

            case "blockquote":
                return self._append_quotation(tag=tag)

            case "br":
                return LatexParser._append_breakline()

            case "cite":
                return self._append_italic(tag=tag)

            case "dl":
                return self._append_description(tag=tag)

            case "em":
                return self._append_emphasis(tag=tag)

            case "hr":
                return LatexParser._append_thematic_break()

            case "i" if tag.has_attr("lang"):
                return self._append_italic(tag=tag)

            case "i":
                return self._append_italic(tag=tag)

            case "j":
                return self._append_enjambment(tag=tag)

            case "ol":
                return self._append_enumerate(tag=tag)

            case "p":
                return self._append_p(tag=tag)

            case "section" if tag.has_attr("id") and tag["id"] == "main-toc":
                return LatexParser._append_tableofcontents()

            case "section" if tag.has_attr("class") and "secondary-toc" in tag["class"]:
                return ""

            case "span":
                return self._append_span(tag=tag)

            case "ul":
                return self._append_itemize(tag=tag)

        return self._process_contents(contents=tag.contents)

    def _process_contents(self, contents: list[PageElement]) -> str:
        tex: str = ""

        for _element in contents:
            if isinstance(_element, Tag):
                tex += self._process_tag(tag=_element)
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
    def _get_shared_template(name: str) -> Template:
        if not LATEX_TEMPLATES_MAPPING:
            raise EnvironmentError(
                "Missing .env_public file or the file lacks required variable LATEX_TEMPLATES_MAPPING."
            )

        try:
            _template_name: str = LATEX_TEMPLATES_MAPPING[name]
        except KeyError:
            raise EnvironmentError(
                f"'LATEX_TEMPLATES_MAPPING' in .env_public file lacks required key-value pair for '{name}' template. "
                f"Example:\n"
                "LATEX_TEMPLATES_MAPPING = '{\n"
                '\t"chapter": "chapter-template.tex",\n'
                '\t"metadata": "metadata-template.xmpdata",\n'
                "}'"
            )

        return LatexParser._get_template(name=_template_name, subdir=LatexParser.SHARED_TEMPLATES_SUBDIR)

    def _get_individual_template(self, volume: Volume) -> Template | None:
        if not INDIVIDUAL_TEMPLATES_MAPPING:
            log.warning(
                "Missing .env_public file or the file lacks variable INDIVIDUAL_TEMPLATES_MAPPING."
                f"Skipping appending individual config template."
            )
            return None

        try:
            _publication_mapping: list[str] | str = INDIVIDUAL_TEMPLATES_MAPPING[self.config.edition.text_uid]
        except KeyError:
            log.warning(
                "'INDIVIDUAL_TEMPLATES_MAPPING' in .env_public file lacks key-value pair for "
                f"'{self.config.edition.text_uid}' individual config template. Example:\n"
                "INDIVIDUAL_TEMPLATES_MAPPING = '{\n"
                '\t"ud": "ud.tex",\n'
                '\t"pli-tv-vi": [\n'
                '\t\t"vinaya-1.tex",\n'
                '\t\t"vinaya-2.tex",\n'
                "\t]\n"
                '"}\'"'
            )
            return None

        if isinstance(_publication_mapping, list):
            _template_name = _publication_mapping[volume.volume_number - 1]
        else:
            _template_name = _publication_mapping

        try:
            return LatexParser._get_template(name=_template_name, subdir=LatexParser.INDIVIDUAL_TEMPLATES_SUBDIR)
        except TemplateNotFound:
            log.warning(f"Template '{_template_name}' for publication/volume specific configuration not found.")
            return None

    def _get_cover_template(
        self, name: str, finalize: Callable[[Any], str] = None, is_individual: bool = False
    ) -> Template:

        _subdir = LatexParser.COVER_TEMPLATES_SUBDIR

        if not is_individual:
            if not COVER_TEMPLATES_MAPPING:
                log.warning("Missing .env_public file or the file lacks variable COVER_TEMPLATES_MAPPING.")

            try:
                _template_name = COVER_TEMPLATES_MAPPING[name].format(
                    publication_type=self.config.edition.publication_type.name
                )
            except KeyError:
                raise SystemExit(
                    "'COVER_TEMPLATES_MAPPING' in .env_public file lacks required key-value pair for "
                    f"'{self.config.edition.text_uid}' cover {name} template. Example:\n"
                    "COVER_TEMPLATES_MAPPING = '{\n"
                    '\t"body": "{publication_type}-body-template.tex",\n'
                    '\t"preamble": "{publication_type}-preamble-template.tex",\n'
                    "}'"
                )
        else:
            _subdir = os.path.join(_subdir, "individual")
            _template_name = name

        try:
            return LatexParser._get_template(name=_template_name, finalize=finalize, subdir=_subdir)
        except TemplateNotFound:
            raise SystemExit(f"Template '{_template_name}' for volume cover not found.")

    @staticmethod
    def _get_template(name: str, finalize: Callable[[Any], str] | None = None, subdir: str = "") -> Template:
        _path = LatexParser.TEX_TEMPLATES_DIR / subdir if subdir else LatexParser.TEX_TEMPLATES_DIR

        try:
            _template_loader: FileSystemLoader = FileSystemLoader(searchpath=_path)
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
                finalize=finalize,
                autoescape=True,
                loader=_template_loader,
            )
            _template_env.filters["wrap_in_z"] = wrap_in_z
            template: Template = _template_env.get_template(name=name)
            return template

        except TemplateNotFound:
            raise TemplateNotFound(f"Template '{name}' is missing.")

    @staticmethod
    def _get_matter_name(matter: Tag) -> str:
        name: str = matter["id"] if matter.has_attr("id") else matter["class"][0] if matter.has_attr("class") else ""
        return name

    def _process_html_element(self, element: PageElement, volume: Volume | None = None) -> str:
        if isinstance(element, Tag) and not (element.has_attr("id") and element["id"] in MATTERS_TO_SKIP):
            if volume and (name := LatexParser._get_matter_name(element)) in MATTERS_WITH_TEX_TEMPLATES:
                _template: Template = LatexParser._get_shared_template(name=name)
                tex = _template.render(
                    **volume.dict(exclude_none=True, exclude_unset=True), images_directory=LatexParser.IMAGES_DIR
                )
                return cast(str, NoEscape(tex))
            else:
                return cast(str, NoEscape(self._process_tag(tag=element)))
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
            _vol_title = volume.volume_translation_title

            if _vol_title:
                _first_heading = html.find("h1").string

                if not _first_heading or _vol_title != _first_heading.strip():
                    _title = _vol_title
                else:  # _vol_title == _first_heading.strip()
                    return

            else:
                _title = self.config.publication.translation_title

            _tag = html.new_tag("h1")
            _tag.string = _title
            doc.append(NoEscape(LatexParser._append_custom_part(tag=_tag)))

    def _append_individual_config(self, doc: Document, volume: Volume) -> None:
        if _template := self._get_individual_template(volume=volume):
            doc.preamble.append(NoEscape(_template.render()))

    def _append_preamble(self, doc: Document, volume: Volume) -> None:
        _template: Template = LatexParser._get_shared_template(name="preamble")
        doc.preamble.append(NoEscape(_template.render(**volume.dict(exclude_none=True, exclude_unset=True))))
        self._append_individual_config(doc=doc, volume=volume)

    def _set_xmpdata(self, volume: Volume) -> None:
        _template: Template = LatexParser._get_shared_template(name="metadata")
        _output = _template.render(**volume.dict(exclude_none=True, exclude_unset=True))
        _path = self.TEMP_DIR / f"{volume.filename}.xmpdata"

        with open(file=_path, mode="wt") as f:
            f.write(_output)

    def _generate_tex(self, volume: Volume) -> Document:
        # setup
        self.endnotes: list[str] | None = volume.endnotes if volume.endnotes else None
        self.section_type: str = "chapter" if self._has_chapter_sutta_title(volume=volume) else "section"

        # create .xmpdata file
        self._set_xmpdata(volume=volume)

        doc = Document(**self._process_document_config(volume=volume, config=self.LATEX_DOCUMENT_CONFIG))

        # set preamble
        self._append_preamble(doc=doc, volume=volume)

        # set frontmatter
        doc.append(Command("frontmatter"))
        for _page in volume.frontmatter:
            _frontmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            LatexParser._remove_all_nav(html=_frontmatter_element)
            doc.append(self._process_html_element(volume=volume, element=_frontmatter_element))

        # set mainmatter
        doc.append(Command("mainmatter"))
        doc.append(Command("pagestyle", "fancy"))
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml")
        self._prepare_mainmatter(volume=volume, doc=doc, html=_mainmatter)

        _mainmatter_elements = _mainmatter.find("body").contents
        for _element in _mainmatter_elements:
            doc.append(self._process_html_element(volume=volume, element=_element))

        # set backmatter
        doc.append(Command("backmatter"))
        for _page in volume.backmatter:
            _backmatter_element: PageElement = BeautifulSoup(_page, "lxml").find("body").next_element
            doc.append(self._process_html_element(volume=volume, element=_backmatter_element))

        return doc

    @no_type_check
    def _process_document_config(self, volume: Volume, config: dict[str, str | tuple[str]]) -> dict[str, str]:
        document_config = copy(config)
        _processed_options: list[str] = []

        for _option in document_config["document_options"]:

            if not (_match := re.search(r"{(\w+)}", _option)) or getattr(volume, _match.group(1)):

                # Divide page width by 2 in epub editions
                if self.config.edition.publication_type == "epub" and _match and _match.group(1) == "page_width":
                    _epub_page_width = re.sub(r"^\d+", lambda x: str(int(x.group(0)) // 2), volume.page_width)
                    _processed_options.append(_option.format(**{_match.group(1): _epub_page_width}))

                else:
                    _processed_options.append(_option.format(**volume.dict()))

        document_config["document_options"] = ",".join(_processed_options)
        return document_config

    def _convert_input_to_tex(self, input_data: Any) -> str:
        _html: PageElement = BeautifulSoup(input_data, "lxml").find("body").next_element
        return self._process_tag(tag=_html).replace("\n\n", "")

    def _generate_cover(self, volume: Volume) -> Document:
        # setup
        doc = Document(**self._process_document_config(volume=volume, config=self.LATEX_COVER_CONFIG))

        # cover preamble
        _preamble_template = self._get_cover_template(name="preamble")
        _individual_template = self._get_cover_template(
            name=get_individual_cover_template_name(volume=volume), is_individual=True
        )
        _preamble = _preamble_template.render(
            **volume.dict(exclude_none=True, exclude_unset=True),
            individual_cover_template=_individual_template.render(images_directory=self.IMAGES_DIR),
        )
        doc.preamble.append(NoEscape(_preamble))

        # cover body
        _body_template = self._get_cover_template(name="body", finalize=self._convert_input_to_tex)
        _body = _body_template.render(**volume.dict(exclude_none=True, exclude_unset=True))
        doc.append(NoEscape(_body))

        return doc
