from dataclasses import asdict

import pytest

from sutta_publisher.shared.config import Config


@pytest.mark.vcr
def test_config_for_publication(scpub1_data):
    pub_config = Config.from_publication("scpub1")

    assert asdict(pub_config) == scpub1_data

    print(pub_config, scpub1_data)


@pytest.mark.vcr
def test_config_for_nonexistent_publication():
    with pytest.raises(ValueError):
        Config.from_publication("nonexistent_pub")
