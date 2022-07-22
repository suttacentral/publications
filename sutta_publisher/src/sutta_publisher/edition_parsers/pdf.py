import logging
import os.path
import tempfile
from typing import Callable

from pylatex import Document, Section

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser

log = logging.getLogger(__name__)


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf

    def _generate_latex(self, volume: Volume) -> Document:
        doc = Document()
        _idx = 0

        # set frontmatter
        for _matter_part in volume.frontmatter:
            _idx += 1
            _section_name = f"section_{_idx}"
            with doc.create(Section(_section_name)):
                doc.append(_matter_part)

        return doc

    def _generate_pdf(self, volume: Volume) -> None:
        log.debug("Generating pdf...")

        _path: str = os.path.join(tempfile.gettempdir(), volume.filename)
        doc = self._generate_latex(volume=volume)
        doc.generate_pdf(filepath=_path, clean_tex=False)
        doc.dumps()

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
