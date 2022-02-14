from pytest_mock import MockerFixture

from sutta_publisher.ingester.helper_functions import (
    _catch_translation_en_column,
    _fetch_possible_refs,
    _filter_refs,
    _flatten_list,
    _reference_to_html,
    _segment_id_to_html,
    _split_ref_and_number,
)


def test_should_check_creating_tuple_from_reference():
    assert _split_ref_and_number("bj7.2") == ("bj", "7.2")
    assert _split_ref_and_number("pts-vp-pli14.2") == ("pts-vp-pli", "14.2")
    assert _split_ref_and_number("invalid-ref2.2") is None
    assert _split_ref_and_number("bj") is None


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


def test_should_check_that_list_of_refs_is_fetched(mocker: MockerFixture):
    from_page = [
        {"edition_set": "ms", "includes": "ms", "name": "Mahasaṅgīti Tipiṭaka, 2010"},
        {
            "edition_set": "pts",
            "includes": ["pts-cs", "pts-vp-pli", "pts-vp-pli1ed", "pts-vp-pli2ed", "pts-vp-en", "vnp"],
            "name": "Pali Text Society",
        },
        {"edition_set": "bj", "includes": "bj", "name": "Buddhajayantītripiṭaka, 1957–1989"},
        {
            "edition_set": "csp",
            "includes": ["csp1ed", "csp2ed", "csp3ed"],
            "name": "Chaṭṭhasaṅgīti Piṭakaṃ, 1st ed 1952–1955, 2nd ed 1956–1962, 3rd ed 1997",
        },
        {"edition_set": "dr", "includes": "dr", "name": "Dayyaraṭṭhassa Saṅgītitepiṭakaṁ, 1987"},
        {"edition_set": "mc", "includes": "mc", "name": "Mahācūḷātepiṭakaṁ, 1960–1990"},
        {"edition_set": "mr", "includes": "mr", "name": "Maramma Tipiṭaka, 1997"},
        {"edition_set": "si", "includes": "si", "name": "Sinhala Tipiṭaka, before 1957"},
        {"edition_set": "km", "includes": "km", "name": "Phratraipiṭakapāḷi (Cambodia), 1958–1969"},
        {"edition_set": "lv", "includes": "lv", "name": "Lāvaraṭṭhassa Tipiṭaka, 1957"},
        {"edition_set": "ndp", "includes": "ndp", "name": "Nālandā Devanāgarī Pāḷi Series Tipiṭaka, 1957–1962"},
        {"edition_set": "cck", "includes": "cck", "name": "Chulachomklao Pāḷi Tipiṭaka, 1893"},
        {"edition_set": "sya", "includes": ["sya1ed", "sya2ed", "sya-all"], "name": "Other Thai editions"},
        {"edition_set": "vri", "includes": "vri", "name": "Vipassanā Research Institute Tipiṭaka, 2537–2542"},
        {"edition_set": "maku", "includes": "maku", "short_name": "Mahāmakut (Milindapañha), 1923"},
    ]
    # patch internal func calls, so we don't need to actually download json from the Internet
    mocker.patch(target="urllib.request.urlopen")
    mocker.patch(target="json.loads", return_value=from_page)

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
