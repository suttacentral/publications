import pytest

from sutta_publisher.edition_parsers.helper_functions import (
    _fetch_possible_refs,
    _filter_refs,
    _flatten_list,
    _process_a_line,
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


@pytest.mark.parametrize(
    "test_reference, expected",
    [("bj7.2", ("bj", "7.2")), ("pts-vp-pli14.2", ("pts-vp-pli", "14.2")), ("invalid-ref2.2", None), ("bj", None)],
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


@pytest.mark.parametrize(
    "test_reference, expected_tag",
    [
        (("bj", "7.2"), "<a class='bj' id='bj7.2'>BJ 7.2</a>"),
        (("pts-vp-pli", "14.2"), "<a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>"),
    ],
)
def test_should_check_creating_html_element_from_reference(test_reference, expected_tag):
    assert _reference_to_html(test_reference) == expected_tag


def test_should_check_that_list_is_flattened():
    irregular_list = ["ms", ["pts-vp-en", "vnp"], "bj"]
    flat_list = ["ms", "pts-vp-en", "vnp", "bj"]
    assert _flatten_list(irregular_list) == flat_list


@pytest.mark.vcr()
def test_should_check_that_list_of_refs_is_fetched(list_of_all_refs):
    assert _fetch_possible_refs() == list_of_all_refs


def test_should_check_intersection_of_two_lists():
    some_refs = [
        ("vnp", "6.6"),
        ("pts-vp-en", "7.9"),
        ("km", "2.2"),
    ]
    accepted = ["bj", "pts-vp-en"]
    assert _filter_refs(references=some_refs, accepted_references=accepted) == [("pts-vp-en", "7.9")]


@pytest.mark.parametrize(
    "test_markup, test_segment, test_text, test_references, expected_line",
    [
        (
            "<p>{}",
            "dn1:0.1",
            "lorem ipsum",
            "vnp1.9, pts-vp-pli14.2",
            "<p><a class='sc-main' id='dn1:0.1'>DN 1:0.1</a><a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>lorem ipsum",
        ),
        (
            "<h1 class='sutta-title'>{}</h1></header>",
            "mn138:0.2",
            "dolor sit",
            "invalid_ref, bj7.9",
            "<h1 class='sutta-title'><a class='sc-main' id='mn138:0.2'>MN 138:0.2</a><a class='bj' id='bj7.9'>BJ 7.9</a>dolor sit</h1></header>",
        ),
    ],
)
def test_should_check_that_a_full_mainmatter_item_is_processed(
    test_markup, test_segment, test_text, test_references, expected_line, list_of_all_refs
):
    assert (
        _process_a_line(
            markup=test_markup,
            segment_id=test_segment,
            text=test_text,
            references=test_references,
            possible_refs=list_of_all_refs,
        )
        == expected_line
    )
