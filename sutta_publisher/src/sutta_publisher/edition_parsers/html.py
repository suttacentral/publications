import logging
import re
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
    TAGS_TO_IGNORE = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "address", "td"]

    def __has_contents_or_belong_to_head(self) -> bool:
        return self.contents or self.name in ["meta", "link", "title"]

    def __is_simple_description_list(self) -> bool:
        return (
            self.name in ["dt", "dd"] and any(e for e in self.contents if isinstance(e, NavigableString) and e != "\n")
        ) or (self.name in ["dt"] and len([e for e in self.contents if e.name == "b"]) == 1)

    def __is_simple_list_item(self) -> bool:
        return (
            self.name in ["li"]
            and self.contents
            and any(e for e in self.contents if isinstance(e, NavigableString))
            and not any(e for e in self.contents if e.name in ["ol", "ul"])
        )

    def __contains_only_one_string(self) -> bool:
        return len(self.contents) == 1 and isinstance(self.contents[0], NavigableString)

    def _should_pretty_print(self, indent_level: int | None) -> bool:
        _original_output = super(CustomTag, self)._should_pretty_print(indent_level)
        return (
            _original_output
            and self.__has_contents_or_belong_to_head()
            and not self.name in self.TAGS_TO_IGNORE
            and not self.__is_simple_description_list()
            and not self.__is_simple_list_item()
            and not self.__contains_only_one_string()
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
        _output = HtmlEdition._apply_pretty_printing(html=_html)

        _path = (self.TEMP_DIR / volume.filename).with_suffix(".html")

        with open(file=_path, mode="wt") as f:
            f.write(_output)

        self.append_volume_file_path(volume=volume, paths=[_path])

    def collect_all(self) -> EditionResult:
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [self.generate_standalone_html]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        return EditionResult(
            file_paths=[file_path for volume in _edition.volumes for file_path in volume.file_paths],
            creator_uid=_edition.volumes[0].creator_uid,
            text_uid=_edition.volumes[0].text_uid,
            publication_type=_edition.volumes[0].publication_type,
            translation_lang_iso=_edition.volumes[0].translation_lang_iso,
        )
