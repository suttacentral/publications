import pytest

from sutta_publisher.shared.config import get_editions_configs
from sutta_publisher.shared.value_objects.edition import EditionType


@pytest.mark.vcr()
def test_should_create_config() -> None:
    publication_number = "scpub3"
    # When
    editions = get_editions_configs(publication_number=publication_number)

    # Then
    assert len(editions) == 3

    html_edition = editions.get_edition(edition=EditionType.html)
    assert html_edition.edition.publication_type == EditionType.html
    assert len(html_edition.edition.volumes) == 1
    html_volume = html_edition.edition.volumes[0]
    assert html_volume.backmatter == ["colophon"]
    assert html_volume.frontmatter == [
        "titlepage",
        "imprint",
        "halftitlepage",
        "./matter/epigraph.html",
        "main-toc",
        "./matter/foreword.html",
        "./matter/preface.html",
        "./matter/introduction.html",
        "./matter/acknowledgements.html",
        "blurbs",
    ]
    assert html_volume.mainmatter == ["mn"]

    assert html_edition.publication.creator_name == "Bhikkhu Sujato"
    assert html_edition.publication.translation_subtitle == "A lucid translation of the Majjhima Nikāya"
    assert html_edition.publication.translation_title == "Middle Discourses"

    epub_edition = editions.get_edition(edition=EditionType.epub)
    assert epub_edition.edition.publication_type == EditionType.epub
    assert len(epub_edition.edition.volumes) == 1


@pytest.mark.vcr()
def test_should_raise_for_missing_publication_number() -> None:
    publication_number = "missing_pub_no"

    with pytest.raises(ValueError):
        get_editions_configs(publication_number=publication_number)
