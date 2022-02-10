import inject
import pytest

from sutta_publisher.engine.main import run
from sutta_publisher.publishers.base import ActivePublishers

from fixtures.publisher import TestPublisher


@pytest.mark.vcr
def test_should_publish_html(injector):
    # Given
    expected_publication = "scpub1"
    injector(publication_number=expected_publication)

    # When
    run()

    # Then
    test_publisher: TestPublisher = inject.instance(ActivePublishers)[0]
    assert expected_publication in test_publisher.published_output, test_publisher.published_output
