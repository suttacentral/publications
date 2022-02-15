import logging

import jinja2

from sutta_publisher.shared.value_objects.results import IngestResult

from .base import Publisher

log = logging.getLogger(__name__)


class HtmlPublisher(Publisher):
    @classmethod
    def publish(cls, result: IngestResult) -> None:
        log.info("** Publishing results: %s", result)
        log.info("** Finished publishing results")

    @staticmethod
    def render_jinja_html(
        template_loc: str = "sutta_publisher/templates",
        file_name: str = "single_page_basic_template.html",
        **context: dict,
    ) -> str:
        return (
            jinja2.Environment(
                autoescape=jinja2.select_autoescape(["html"]), loader=jinja2.FileSystemLoader(template_loc + "/")
            )
            .get_template(file_name)
            .render(context)
        )
