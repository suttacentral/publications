from sutta_publisher.shared.value_objects.edition import EditionType

from .base import EditionParser


class PdfEdition(EditionParser):
    edition_type = EditionType.pdf
