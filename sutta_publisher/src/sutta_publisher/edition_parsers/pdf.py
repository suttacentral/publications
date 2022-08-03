import logging
import os.path
import tempfile
from typing import Callable

from bs4 import BeautifulSoup, NavigableString, PageElement, Tag
from pylatex import Document, NewPage, NoEscape, Section, Tabular
from pylatex.base_classes import Command, Environment, UnsafeCommand
from pylatex.package import Package
from pylatex.section import Chapter

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class AsideEnv(Environment):
    _latex_name = "aside"
    packages = [Package("mdframed")]


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf

    def _process_tag(self, doc: Document, tag: Tag) -> None:
        if tag.has_attr("class") and any(_class in tag["class"] for _class in ["range-title", "sutta-title"]):
            # acronym, trans_title, root_title = tag.stripped_strings
            doc.append(Section(title=" ".join(tag.stripped_strings), numbering=False, label=tag.parent.id))

        elif tag.has_attr("class") and "section-title" in tag["class"]:
            doc.append(NewPage())
            doc.append(Chapter(title=tag.string.strip(), numbering=False, label=tag.id))

        elif tag.name == "br":
            doc.append(NoEscape(r"\\"))

        elif tag.name == "p":
            self._process_contents(doc=doc, contents=tag.contents)
            if tag.next_sibling and not tag.next_sibling.name == "blockquote":
                doc.append(NoEscape(r"\\"))

        elif tag.name == "blockquote":
            with doc.create(Environment()) as _env:
                _env._latex_name = "verse"
                self._process_contents(doc=doc, contents=tag.contents)

        elif tag.name == "aside":
            with doc.create(AsideEnv()):
                self._process_contents(doc=doc, contents=tag.contents)

        elif tag.name == "table":
            _rows: int = max(len([_td for _td in _tr.find_all("td")]) for _tr in tag.find_all("tr"))
            _table_spec: str = " ".join("l" for _ in range(_rows))
            _has_head: bool = bool(tag.find("th"))

            with doc.create(Tabular(table_spec=_table_spec)) as _table:
                if _has_head:
                    _table.add_row([_th.string for _th in tag.find_all("th")])
                    _table.end_table_header()
                for _row in tag.find_all("tr"):
                    _table.add_row([_td.string for _td in _row.find_all("td")])
            doc.append(NoEscape(r"\\"))

        elif tag.name == "address":
            doc.append(
                Command(
                    "address",
                    NoEscape(
                        r"\\".join(_el for _el in tag.contents if isinstance(_el, NavigableString) and _el != "\n")
                    ),
                )
            )

        else:
            self._process_contents(doc=doc, contents=tag.contents)

    def _process_contents(self, doc: Document, contents: list[PageElement]) -> None:
        for _element in contents:
            if isinstance(_element, Tag):
                self._process_tag(doc=doc, tag=_element)
            elif isinstance(_element, NavigableString) and _element != "\n":
                doc.append(_element)
            else:
                pass

    def _generate_latex(self, volume: Volume) -> Document:
        doc = Document(documentclass="book")

        # set packages
        doc.packages.append(Package("mdframed"))
        doc.packages.append(Package("verse"))

        # set additional commands
        doc.append(
            UnsafeCommand(
                "newenvironment",
                "aside",
                extra_arguments=[
                    r"\begin{mdframed}[style=0,leftline=false,rightline=false,topline=false,bottomline=false,leftmargin=2em,rightmargin=2em,innerleftmargin=0pt,innerrightmargin=0pt,linewidth=0.75pt,skipabove=7pt,skipbelow=7pt]\small",
                    r"\end{mdframed}",
                ],
            )
        )

        # set frontmatter
        # doc.append(Command("frontmatter"))
        # for _part in volume.frontmatter:
        #     _element = BeautifulSoup(_part, "lxml").find("body").next_element
        #     if isinstance(_element, Tag) and _element.has_attr("id") and _element["id"] == "main-toc":
        #         continue
        #     doc.append(NewPage())
        #     if isinstance(_element, Tag):
        #         self._process_tag(doc=doc, tag=_element)
        #     elif isinstance(_element, NavigableString) and _element != "\n":
        #         doc.append(_element)
        #     else:
        #         pass

        # set mainmatter
        doc.append(Command("mainmatter"))
        _mainmatter = BeautifulSoup(volume.mainmatter, "lxml").find("body")
        for _element in _mainmatter:
            if isinstance(_element, Tag):
                self._process_tag(doc=doc, tag=_element)
            else:
                doc.append(_element)

        # set backmatter
        # doc.append(Command("backmatter"))
        # for _part in volume.backmatter:
        #     _matter = BeautifulSoup(_part, "lxml").find("body")
        #     for _element in _matter:
        #         if isinstance(_element, Tag):
        #             self._process_tag(doc=doc, tag=_element)
        #         else:
        #             doc.append(_element)

        return doc

    def _generate_pdf(self, volume: Volume) -> None:
        log.debug("Generating pdf...")

        _path: str = os.path.join(tempfile.gettempdir(), volume.filename[:-4])
        doc = self._generate_latex(volume=volume)
        doc.generate_pdf(filepath=_path, clean_tex=False, compiler="latexmk")

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
