import logging
from typing import Callable

from PyPDF2 import PdfReader

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser
from .latex import LatexParser

log = logging.getLogger(__name__)


class PaperbackEdition(LatexParser):
    edition_type = EditionType.paperback
    spine_width: float | None

    def _generate_paperback(self, volume: Volume) -> None:
        log.debug(f"Generating paperback... (vol {volume.volume_number or 1} of {len(self.config.edition.volumes)})")

        _path = self.TEMP_DIR / volume.filename
        log.debug("Generating tex...")
        doc = self._generate_latex(volume=volume)
        # doc.generate_tex(filepath=str(_path))  # dev
        log.debug("Generating pdf...")
        doc.generate_pdf(filepath=str(_path), clean_tex=False, compiler="latexmk", compiler_args=["-lualatex"])

    def _calculate_spine_width(self, volume: Volume) -> None:
        _pdf_file_path = self.TEMP_DIR / f"{volume.filename}.pdf"

        if _pdf_file_path.exists():
            log.debug("Calculating spine width...")
            _number_of_pages = len(PdfReader(_pdf_file_path).pages)

            # Lulu formula for spine width calculation
            self.spine_width = (_number_of_pages / 444) + 0.06

    def collect_all(self):  # type: ignore
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [
            self._generate_paperback,
            self._calculate_spine_width,
        ]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        # self.generate_paperback()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
