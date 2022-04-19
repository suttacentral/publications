import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

import jinja2
from jinja2 import Environment, FileSystemLoader, Template

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class HtmlEdition(EditionParser):
    CSS_PATH: Path = Path(__file__).parent.parent / "css_stylesheets/standalone_html.css"
    edition_type: EditionType = EditionType.html

    def _get_css(self) -> str:
        """Returns css stylesheet as a string"""

        with open(self.CSS_PATH, "r") as css_file:
            content = css_file.read()

        return content

    def generate_standalone_html(self, volume: Volume) -> None:
        log.debug("Generating a standalone html...")

        _template_loader: FileSystemLoader = jinja2.FileSystemLoader(searchpath=HtmlEdition.HTML_TEMPLATES_DIR)
        _template_env: Environment = jinja2.Environment(loader=_template_loader, autoescape=True)
        _template: Template = _template_env.get_template(name="standalone_template.html")
        _css: str = self._get_css()

        # Generating output HTML
        _output = _template.render(
            css=_css, frontmatter=volume.frontmatter, mainmatter=volume.mainmatter, backmatter=volume.backmatter
        )

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
