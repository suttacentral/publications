import logging
import tempfile
from pathlib import Path
from typing import Callable

from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType
from sutta_publisher.shared.value_objects.parser_objects import Edition, Volume

from .base import EditionParser
from .latex import LatexEdition

log = logging.getLogger(__name__)


class PaperbackEdition(LatexEdition):
    edition_type = EditionType.paperback

    def _generate_paperback(self, volume: Volume) -> None:
        log.debug(f"Generating paperback... (vol {volume.volume_number or 1} of {len(self.config.edition.volumes)})")

        _path = Path(tempfile.gettempdir()) / volume.filename
        log.debug("Generating tex...")
        doc = self._generate_latex(volume=volume)
        # doc.generate_tex(filepath=_path)  # dev
        log.debug("Generating pdf...")
        doc.generate_pdf(filepath=_path, clean_tex=False, compiler="latexmk", compiler_args=["-lualatex"])

    def collect_all(self):  # type: ignore
        _edition: Edition = super().collect_all()

        _operations: list[Callable] = [self._generate_paperback]

        for _operation in _operations:
            EditionParser.on_each_volume(edition=_edition, operation=_operation)

        # self.generate_paperback()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
