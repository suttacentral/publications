from dataclasses import asdict

import pytest

from sutta_publisher.shared.config import Config


@pytest.mark.vcr
def test_config_for_publication(scpub1_data):
    pub_config = Config.from_publication("scpub1")

    assert scpub1_data.publication_number == pub_config.publication_number
    assert scpub1_data.creator_name == pub_config.creator_name
    assert scpub1_data.translation_title == pub_config.translation_title
    assert scpub1_data.translation_subtitle == pub_config.translation_subtitle
    assert scpub1_data.root_title == pub_config.root_title
    assert scpub1_data.editions == pub_config.editions


@pytest.mark.vcr
def test_config_for_nonexistent_publication():
    with pytest.raises(ValueError):
        Config.from_publication("nonexistent_pub")
