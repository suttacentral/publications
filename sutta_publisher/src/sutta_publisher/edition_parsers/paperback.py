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

    def generate_paperback(self, volume: Volume) -> None:
        log.debug(
            f"Generating paperback... (vol {volume.volume_number or 1} of {self.config.edition.number_of_volumes})"
        )
        _path = self.TEMP_DIR / volume.filename
        log.debug("Generating tex...")
        doc = self._generate_tex(volume=volume)
        # doc.generate_tex(filepath=str(_path))  # dev
        log.debug("Generating pdf...")
        doc.generate_pdf(filepath=str(_path), clean_tex=False, compiler="latexmk", compiler_args=["-lualatex"])

        volume.output_file_paths.extend(
            (_path.with_suffix(".tex"), _path.with_suffix(".pdf")),
        )

    def calculate_spine_width(self, volume: Volume) -> None:
        _pdf_file_path = self.TEMP_DIR / f"{volume.filename}.pdf"

        if _pdf_file_path.exists():
            log.debug("Calculating spine width...")
            _number_of_pages = len(PdfReader(_pdf_file_path).pages)

            # Lulu formula for spine width calculation
            _spine_width = (_number_of_pages / 444) + 0.06

            volume.spine_width = f"{_spine_width}in"

    def generate_cover(self, volume: Volume) -> None:
        log.debug(f"Generating cover... (vol {volume.volume_number or 1} of {self.config.edition.number_of_volumes})")

        _path = self.TEMP_DIR / volume.cover_filename
        doc = self._generate_cover(volume=volume)
        # doc.generate_tex(filepath=str(_path))  # dev
        log.debug("Generating pdf...")
        doc.generate_pdf(filepath=str(_path), clean_tex=False, compiler="latexmk", compiler_args=["-lualatex"])

        volume.output_file_paths.extend(
            (
                _path.with_suffix(".tex"),
                _path.with_suffix(".pdf"),
                _path.with_suffix(".xmpdata"),
            ),
        )

    def collect_all(self) -> EditionResult:
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [
            self.generate_paperback,
            self.calculate_spine_width,
            self.generate_cover,
        ]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        return EditionResult(
            file_paths=[file_path for volume in _edition.volumes for file_path in volume.output_file_paths]
        )
