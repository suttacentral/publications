import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Callable

import jinja2
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from jinja2 import Environment, FileSystemLoader, Template

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class CustomTag(Tag):
    def _should_pretty_print(self, indent_level: int | None) -> bool:
        return (
            indent_level is not None
            and (not self.preserve_whitespace_tags or self.name not in self.preserve_whitespace_tags)
            and (self.contents or self.name in ["meta", "link"])
            and not (self.name in ["p", "h1", "h2", "h3", "h4", "h5", "h6", "address", "td"])
            and not (
                self.name in ["dt", "dd"] and [e for e in self.contents if isinstance(e, NavigableString) and e != "\n"]
            )
            and not (self.name in ["dt"] and len([e for e in self.contents if e.name == "b"]) == 1)
            and not (self.contents and len(self.contents) == 1 and isinstance(self.contents[0], NavigableString))
            and not (
                self.name in ["li"]
                and self.contents
                and [e for e in self.contents if isinstance(e, NavigableString)]
                and not [e for e in self.contents if e.name in ["ol", "ul"]]
            )
        )


class HtmlEdition(EditionParser):
    CSS_PATH: Path = Path(__file__).parent.parent / "css_stylesheets/standalone_html.css"
    edition_type: EditionType = EditionType.html

    def _get_css(self) -> str:
        """Returns css stylesheet as a string"""

        with open(self.CSS_PATH, "r") as css_file:
            content = css_file.read()

        return content

    @staticmethod
    def _apply_pretty_printing(html: str) -> str:
        """Returns prettified html with no indent and custom breakline conditions"""
        _element_classes = {Tag: CustomTag}
        _soup = BeautifulSoup(html, "lxml", element_classes=_element_classes)
        return re.compile(r"^(\s*)", re.MULTILINE).sub("", _soup.prettify(formatter=None))

    def generate_standalone_html(self, volume: Volume) -> None:
        log.debug("Generating a standalone html...")

        _template_loader: FileSystemLoader = jinja2.FileSystemLoader(searchpath=HtmlEdition.HTML_TEMPLATES_DIR)
        _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)
        _template: Template = _template_env.get_template(name="book-template.html")
        _css: str = self._get_css()

        # Generating output HTML
        _html = _template.render(css=_css, **volume.dict(exclude_none=True, exclude_unset=True))
        _output = self._apply_pretty_printing(html=_html)

        _path: str = os.path.join(tempfile.gettempdir(), volume.filename)

        with open(file=_path, mode="wt") as f:
            f.write(_output)

    def collect_all(self) -> EditionResult:
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [self.generate_standalone_html]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
