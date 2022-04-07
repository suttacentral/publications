import logging
import os
import tempfile

import jinja2

from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

log = logging.getLogger(__name__)


class HtmlEdition(EditionParser):
    CSS_PATH = os.path.dirname(__file__) + "/css_stylesheets/standalone_html.css"
    HTML_TEMPLATE = os.path.dirname(__file__) + "/html_templates/standalone_template.html"
    edition_type = EditionType.html

    def __get_css(self) -> str:
        """Returns css stylesheet as a string"""

        with open(self.CSS_PATH, "r") as css_file:
            content = css_file.read()

        return content

    def __generate_standalone_html(self) -> None:
        log.debug("Generating html...")

        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader, autoescape=True)
        template = template_env.get_template(self.HTML_TEMPLATE)
        css: str = self.__get_css()

        for _frontmatters, (_vol_nr, _volume) in zip(self.per_volume_frontmatters, enumerate(self.per_volume_html)):
            output_volume = template.render(css=css, frontmatters=_frontmatters.values(), mainmatter=_volume)

            _path = os.path.join(
                tempfile.gettempdir(), f"{self.config.publication.translation_title} vol {_vol_nr + 1}.html"
            )

            try:
                with open(file=_path, mode="w") as f:
                    f.write(output_volume)
            except IOError as e:
                log.error(f"Failed to write {_path} due to IO error: {e}")

    def collect_all(self) -> EditionResult:
        super().collect_all()
        # self.__generate_backmatter()
        self.__generate_standalone_html()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
