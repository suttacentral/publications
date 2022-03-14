import pytest

from sutta_publisher.shared.config import get_edition_config
from sutta_publisher.shared.data import get_edition_data
from sutta_publisher.shared.value_objects.edition_data import MainMatterDetails


@pytest.mark.vcr()
def test_should_return_data_for_edition() -> None:
    # Given
    edition_config = get_edition_config(edition_id="mn-en-sujato_scpub3-ed2-epub_2022-02-10")
    # When
    edition_data = get_edition_data(edition_config=edition_config)
    # Then
    assert len(edition_data) == 1

    first_edition_data = edition_data[0]
    assert len(first_edition_data.mainmatter) == 171

    first_mainmatter_chunk = first_edition_data.mainmatter[0]
    assert first_mainmatter_chunk.blurb is not None
    assert first_mainmatter_chunk.mainmatter == MainMatterDetails(main_text=None, markup=None, reference=None)
    assert first_mainmatter_chunk.name == "Middle Discourses Collection"
    assert first_mainmatter_chunk.type == "branch"

    some_mainmatter_chunk = first_edition_data.mainmatter[20]
    assert some_mainmatter_chunk.blurb == (
        "While living in the wilderness is great, not everyone is ready for it. "
        "The Buddha encourages meditators to reflect on whether one’s environment is genuinely supporting their meditation practice, "
        "and if not, to leave."
    )
    assert set(some_mainmatter_chunk.mainmatter.main_text) & {"mn17:0.1", "mn17:0.2", "mn17:1.1", "mn17:1.2"}
    assert set(some_mainmatter_chunk.mainmatter.markup) & {"mn17:0.1", "mn17:0.2", "mn17:1.1", "mn17:1.2"}
    assert set(some_mainmatter_chunk.mainmatter.reference) & {"mn17:1.1", "mn17:10.1", "mn17:11.1", "mn17:12.1"}
    assert some_mainmatter_chunk.name == "Jungle Thickets "
    assert some_mainmatter_chunk.type == "leaf"

    assert set(first_edition_data.extras) & {
        "./matter/acknowledgements.html",
        "./matter/foreword.html",
        "./matter/img/epub_cover.png",
        "./matter/introduction.html",
    }

    # Check for if `volume_details.mainmatter` has more elements than only one
    assert len(edition_data[-1].mainmatter) == 171