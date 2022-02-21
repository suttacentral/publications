import pytest

from sutta_publisher.edition_parsers.helper_functions import (
    _catch_translation_en_column,
    _fetch_possible_refs,
    _filter_refs,
    _flatten_list,
    _reference_to_html,
    _segment_id_to_html,
    _split_ref_and_number,
)


@pytest.fixture
def list_of_all_refs():
    return [
        "ms",
        "pts-cs",
        "pts-vp-pli",
        "pts-vp-pli1ed",
        "pts-vp-pli2ed",
        "pts-vp-en",
        "vnp",
        "bj",
        "csp1ed",
        "csp2ed",
        "csp3ed",
        "dr",
        "mc",
        "mr",
        "si",
        "km",
        "lv",
        "ndp",
        "cck",
        "sya1ed",
        "sya2ed",
        "sya-all",
        "vri",
        "maku",
    ]


@pytest.fixture
@pytest.mark.parametrize(
    "test_reference, expected",
    [("bj7.2", ("bj", "7.2")), ("pts-vp-pli14.2", ("bj", "7.2")), ("invalid-ref2.2", None), ("bj", None)],
)
def test_should_check_creating_tuple_from_reference(test_reference, expected, list_of_all_refs):
    assert _split_ref_and_number(test_reference, list_of_all_refs) == expected


@pytest.mark.parametrize(
    "test_segment_id, expected_html",
    [
        ("dn1:0.1", "<a class='sc-main' id='dn1:0.1'>DN 1:0.1</a>"),
        ("dn1:1.1.4", "<a class='sc-main' id='dn1:1.1.4'>DN 1:1.1.4</a>"),
    ],
)
def test_should_check_html_element_is_created_from_segment_id(test_segment_id, expected_html):
    assert _segment_id_to_html(test_segment_id) == expected_html


def test_should_find_first_english_translation_column():
    column_names1 = [
        "translation-de-sabbamitta",
        "translation-en-sujato",
        "translation-en-second",
        "translation-pl-hardao",
        "variant-pli-ms",
    ]
    assert _catch_translation_en_column(column_names1) == "translation-en-sujato"


def test_shouldnt_find_any_english_translation_column():
    column_names2 = [
        "segment_id",
        "translation-de-sabbamitta",
        "html",
    ]
    assert _catch_translation_en_column(column_names2) is None


@pytest.fixture
@pytest.mark.parametrize(
    "test_reference, expected_tag",
    [
        ("bj7.2", "<a class='bj' id='bj7.2'>BJ 7.2</a>"),
        ("pts-vp-pli14.2", "<a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>"),
        ("wrong-reference", ""),
    ],
)
def test_should_check_creating_html_element_from_reference(test_reference, expected_tag, list_of_all_refs):
    assert _reference_to_html(test_reference, list_of_all_refs) == expected_tag


def test_should_check_that_list_is_flattened():
    irregular_list = ["ms", ["pts-vp-en", "vnp"], "bj"]
    flat_list = ["ms", "pts-vp-en", "vnp", "bj"]
    assert _flatten_list(irregular_list) == flat_list


@pytest.fixture
@pytest.mark.vcr
def test_should_check_that_list_of_refs_is_fetched(list_of_all_refs):
    assert _fetch_possible_refs() == list_of_all_refs


def test_should_check_intersection_of_two_lists():
    some_refs = [
        "vnp",
        "pts-vp-en",
        "km",
    ]
    accepted = ["bj", "pts-vp-en"]
    assert _filter_refs(refs=some_refs, accepted_refs=accepted) == ["pts-vp-en"]
