from sutta_publisher.shared.value_objects.edition import EditionResult, EditionType

from .base import EditionParser


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf

    def __generate_pdf(self):  # type: ignore
        pass

    def collect_all(self):  # type: ignore
        super().collect_all()
        # self.__generate_backmatter()
        self.__generate_pdf()
        txt = "dummy"
        result = EditionResult()
        result.write(txt)
        result.seek(0)
        return result
