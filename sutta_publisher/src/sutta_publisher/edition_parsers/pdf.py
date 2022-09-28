import logging
from typing import Callable

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser
from .latex import LatexParser

log = logging.getLogger(__name__)


class PdfEdition(LatexParser):
    edition_type = EditionType.pdf

    def _generate_pdf(self, volume: Volume) -> None:
        log.debug("Generating pdf...")

        _path = self.TEMP_DIR / volume.filename
        doc = self._generate_tex(volume=volume)
        doc.generate_pdf(filepath=str(_path), clean_tex=False, compiler="latexmk")

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
