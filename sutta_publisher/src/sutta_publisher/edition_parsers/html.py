import logging
from pathlib import Path

import jinja2

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser

log = logging.getLogger(__name__)


class HtmlEdition(EditionParser):
    CSS_PATH = Path(__file__).parent.parent / "css_stylesheets/standalone_html.css"
    edition_type = EditionType.html

    def __get_css(self) -> str:
        """Returns css stylesheet as a string"""

        with open(self.CSS_PATH, "r") as css_file:
            content = css_file.read()

        return content

    def __generate_standalone_html(self) -> None:
        log.debug("Generating html...")

        template_loader = jinja2.FileSystemLoader(searchpath=HtmlEdition.HTML_TEMPLATES_DIR)
        template_env = jinja2.Environment(loader=template_loader, autoescape=True)
        template = template_env.get_template(name="standalone_template.html")
        css: str = self.__get_css()

        # Generating output HTML
        for _frontmatters, (_vol_nr, _volume) in zip(self.per_volume_frontmatters, enumerate(self.per_volume_html)):
            output_volume = template.render(css=css, frontmatters=list(_frontmatters.values()), mainmatter=_volume)

    def collect_all(self) -> EditionResult:
        super().collect_all()
        # self.__generate_backmatter()
        self.__generate_standalone_html()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
