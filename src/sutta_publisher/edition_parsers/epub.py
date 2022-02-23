from sutta_publisher.shared.value_objects.edition import EditionType

from .base import EditionParser


class EpubEdition(EditionParser):
    edition_type = EditionType.epub
