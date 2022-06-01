import pytest

from sutta_publisher.shared.config import get_edition_config
from sutta_publisher.shared.data import get_edition_data
from sutta_publisher.shared.value_objects.edition_data import NodeDetails


@pytest.mark.vcr()
def test_should_return_data_for_edition() -> None:
    # Given
    edition_config = get_edition_config(edition_id="mn-en-sujato_scpub3-ed2-epub_2022-02-10")
    # When
    edition_data = get_edition_data(edition_config=edition_config)
    # Then
    assert len(edition_data) == 1

    first_edition_data = edition_data[0]
    assert len(first_edition_data.mainmatter[0]) == 171

    first_mainmatter_node = first_edition_data.mainmatter[0][0]
    assert first_mainmatter_node.blurb is not None
    assert first_mainmatter_node.mainmatter == NodeDetails(main_text=None, markup=None, reference=None)
    assert first_mainmatter_node.name == "Middle Discourses Collection"
    assert first_mainmatter_node.type == "branch"

    some_mainmatter_node = first_edition_data.mainmatter[0][20]
    assert some_mainmatter_node.blurb == (
        "While living in the wilderness is great, not everyone is ready for it. "
        "The Buddha encourages meditators to reflect on whether one’s environment is genuinely supporting their meditation practice, "
        "and if not, to leave."
    )
    assert set(some_mainmatter_node.mainmatter.main_text) & {"mn17:0.1", "mn17:0.2", "mn17:1.1", "mn17:1.2"}
    assert set(some_mainmatter_node.mainmatter.markup) & {"mn17:0.1", "mn17:0.2", "mn17:1.1", "mn17:1.2"}
    assert set(some_mainmatter_node.mainmatter.reference) & {"mn17:1.1", "mn17:10.1", "mn17:11.1", "mn17:12.1"}
    assert some_mainmatter_node.name == "Jungle Thickets "
    assert some_mainmatter_node.type == "leaf"

    assert set(first_edition_data.extras) & {
        "./matter/acknowledgements.html",
        "./matter/foreword.html",
        "./matter/img/epub_cover.png",
        "./matter/introduction.html",
    }

    # Check if `volume_details.mainmatter` has more elements than only one
    assert len(edition_data[-1].mainmatter[0]) == 171
