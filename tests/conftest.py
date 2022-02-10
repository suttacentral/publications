from typing import Callable

import pytest

from sutta_publisher.publishers.base import ActivePublishers
from sutta_publisher.shared.config import setup_inject

from fixtures.publisher import TestPublisher


@pytest.fixture
def injector() -> Callable:
    """Configure application for the tests."""

    def _injector(publication_number: str = "test_publication", bindings: dict = None) -> None:
        bindings = bindings or {}
        actual_bindings = {ActivePublishers: ActivePublishers([TestPublisher()])}
        actual_bindings.update(bindings)
        setup_inject(publication_number=publication_number, bindings=actual_bindings)

    return _injector


@pytest.fixture
def scpub1_data() -> dict:
    """Data of scpub1 publication."""

    data: dict = {
        "publication_number": "scpub1",
        "root_lang_iso": "pli",
        "root_lang_name": "Pali",
        "translation_lang_iso": "en",
        "translation_lang_name": "English",
        "source_url": "https://github.com/suttacentral/bilara-data/tree/master/translation/en/sujato/sutta/kn/thag",
        "creator_uid": "sujato",
        "creator_name": "Bhikkhu Sujato",
        "creator_github_handle": "sujato",
        "text_uid": "thag",
        "translation_title": "Verses of the Senior Monks",
        "translation_subtitle": "An approachable translation of the Theragāthā",
        "root_title": "Theragāthā",
        "creation_process": "Translated from the Pali. Primary source was the Mahāsaṅgīti edition, with reference to several English translations, especially those of K.R. Norman.",
        "text_description": "This translation aims to make a clear, readable, and accurate rendering of the Theragāthā. The initial edition was by Jessica Walton and Bhikkhu Sujato was published in 2014 through SuttaCentral. A revised edition, bringing the terminology in line with the subsequently-translated four Nikāyas, was published in 2019.",
        "is_published": True,
        "publication_status": "Completed, revision is ongoing.",
        "license_type": "Creative Commons Zero",
        "license_abbreviation": "CC0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "license_statement": "This translation is an expression of an ancient spiritual text that has been passed down by the Buddhist tradition for the benefit of all sentient beings. It is dedicated to the public domain via Creative Commons Zero (CC0). You are encouraged to copy, reproduce, adapt, alter, or otherwise make use of this translation. The translator respectfully requests that any use be in accordance with the values and principles of the Buddhist community.",
        "first_published": "2014",
        "editions_url": "",
    }

    # TODO: remove below dummy editions when Config class is fully functional
    data["editions"] = {"key1": "val1", "key2": "val1", "key3": "val1", "key4": {"key1": "val1", "key2": "val"}}

    return data
