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


def test_should_check_creating_tuple_from_reference():
    list_of_refs = [
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
    assert _split_ref_and_number("bj7.2", list_of_refs) == ("bj", "7.2")
    assert _split_ref_and_number("pts-vp-pli14.2", list_of_refs) == ("pts-vp-pli", "14.2")
    assert _split_ref_and_number("invalid-ref2.2", list_of_refs) is None
    assert _split_ref_and_number("bj", list_of_refs) is None


def test_should_check_html_element_is_created_from_segment_id():
    assert _segment_id_to_html("dn1:0.1") == f"<a id='dn1:0.1'></a>"
    assert _segment_id_to_html("dn1:1.1.4") == f"<a id='dn1:1.1.4'></a>"


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


def test_should_check_creating_html_element_from_reference():
    assert _reference_to_html(("bj", "7.2")) == "<a class='bj' id='bj7.2'>BJ 7.2</a>"
    assert _reference_to_html(("pts-vp-pli", "14.2")) == "<a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>"


def test_should_check_that_list_is_flattened():
    irregular_list = ["ms", ["pts-vp-en", "vnp"], "bj"]
    flat_list = ["ms", "pts-vp-en", "vnp", "bj"]
    assert _flatten_list(irregular_list) == flat_list


@pytest.mark.vcr
def test_should_check_that_list_of_refs_is_fetched():
    list_of_refs = [
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

    assert _fetch_possible_refs() == list_of_refs


def test_should_check_intersection_of_two_lists():
    some_refs = [
        "vnp",
        "pts-vp-en",
        "km",
    ]
    accepted = ["bj", "pts-vp-en"]
    assert _filter_refs(refs=some_refs, accepted_refs=accepted) == ["pts-vp-en"]
