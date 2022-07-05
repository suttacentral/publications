import pytest

from sutta_publisher.edition_parsers.base import RELATIVE_LINKS_PATTERN
from sutta_publisher.edition_parsers.helper_functions import (
    _filter_refs,
    _flatten_list,
    _reference_to_html,
    _split_ref_and_number,
    fetch_possible_refs,
    process_line,
    process_links,
    validate_node,
)
from sutta_publisher.shared.value_objects.edition_data import Node, NodeDetails


@pytest.fixture
def list_of_all_refs() -> set[str]:
    return {
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
    }


@pytest.mark.parametrize(
    "test_reference, expected",
    [("bj7.2", ("bj", "7.2")), ("pts-vp-pli14.2", ("pts-vp-pli", "14.2")), ("invalid-ref2.2", None), ("bj", None)],
)
def test_should_check_creating_tuple_from_reference(
    test_reference: str, expected: tuple[str, str] | None, list_of_all_refs: list[str]
) -> None:
    assert _split_ref_and_number(test_reference, list_of_all_refs) == expected


@pytest.mark.parametrize(
    "test_reference, expected_tag",
    [
        (("bj", "7.2"), "<a class='bj' id='bj7.2'>BJ 7.2</a>"),
        (("pts-vp-pli", "14.2"), "<a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>"),
    ],
)
def test_should_check_creating_html_element_from_reference(test_reference: tuple[str, str], expected_tag: str) -> None:
    assert _reference_to_html(test_reference) == expected_tag


def test_should_check_that_list_is_flattened() -> None:
    irregular_list = ["ms", ["pts-vp-en", "vnp"], "bj"]
    flat_list = ["ms", "pts-vp-en", "vnp", "bj"]
    assert _flatten_list(irregular_list) == flat_list


@pytest.mark.vcr()
def test_should_check_that_list_of_refs_is_fetched(list_of_all_refs: list[str]) -> None:
    assert fetch_possible_refs() == list_of_all_refs


def test_should_check_intersection_of_two_lists() -> None:
    some_refs = [
        ("vnp", "6.6"),
        ("pts-vp-en", "7.9"),
        ("km", "2.2"),
    ]
    accepted = ["bj", "pts-vp-en"]
    assert _filter_refs(references=some_refs, accepted_references=accepted) == [("pts-vp-en", "7.9")]


@pytest.mark.parametrize(
    "test_markup, test_segment, test_text, test_note, test_references, expected_line, accepted_references",
    [
        (
            "<p>{}",
            "dn1:0.1",
            "lorem ipsum",
            "test note for lorem ipsum",
            "vnp1.9, pts-vp-pli14.2",
            "<p data-ref='dn1:0.1'><a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>lorem ipsum<a href='#note-{number}' id='noteref-{number}' role='doc-noteref' epub:type='noteref'>{number}</a>",
            ["pts-vp-pli"],
        ),
        (
            "<h1 class='sutta-title'>{}</h1></header>",
            "mn138:0.2",
            "dolor sit",
            "test note for dolor sit",
            "invalid_ref, bj7.9",
            "<h1 class='sutta-title'><a class='bj' id='bj7.9'>BJ 7.9</a>dolor sit<a href='#note-{number}' id='noteref-{number}' role='doc-noteref' epub:type='noteref'>{number}</a></h1></header>",
            ["bj"],
        ),
    ],
)
def test_should_check_that_a_full_mainmatter_item_is_processed(
    monkeypatch,
    test_markup: str,
    test_segment: str,
    test_text: str,
    test_note: str,
    test_references: str,
    expected_line: str,
    accepted_references: list[str],
    list_of_all_refs: set[str],
) -> None:
    monkeypatch.setattr("sutta_publisher.edition_parsers.helper_functions.ACCEPTED_REFERENCES", accepted_references)
    assert (
        process_line(
            markup=test_markup,
            segment_id=test_segment,
            text=test_text,
            note=test_note,
            references=test_references,
            possible_refs=list_of_all_refs,
        )
        == expected_line
    )


@pytest.mark.parametrize(
    "html, acronym, mainmatter_uids, expected_link, expected_mismatches",
    [
        # relative links
        (
            '<a href="/snp5.13/en/sujato#4.3">Snp 5.13:4.3</a>',
            "snp",
            ["snp5.13:4.3"],
            '<a href="#snp5.13:4.3">Snp 5.13:4.3</a>',
            [],
        ),
        ('<a href="/mn-abcdef">MN 1</a>', "mn", ["mn-abcdef"], '<a href="#mn-abcdef">MN 1</a>', []),
        (
            '<a href="/snp5.13#4.3">Snp 5.13:4.3</a>',
            "snp",
            ["snp5.13:4.3"],
            '<a href="#snp5.13:4.3">Snp 5.13:4.3</a>',
            [],
        ),
        ('<a href="/snp1">Snp 1</a>', "snp", ["snp1"], '<a href="#snp1">Snp 1</a>', []),
        ('<a href="snp1">Snp 1</a>', "snp", ["snp1"], '<a href="#snp1">Snp 1</a>', []),
        ('<a href="snp-test">The Great Book</a>', "snp", ["snp-test"], '<a href="#snp-test">The Great Book</a>', []),
        ('<a href="/sn1#2">SN 1:2</a>', "sn", ["sn1:2"], '<a href="#sn1:2">SN 1:2</a>', []),
        ('<a href="/snp1.1-2#2">Snp 1:1</a>', "snp", ["snp1.1-2:2"], '<a href="#snp1.1-2:2">Snp 1:1</a>', []),
        ('<a href="/an1#2-2">AN 1:2-2</a>', "an", ["an1:2-2"], '<a href="#an1:2-2">AN 1:2-2</a>', []),
        (
            '<a href="https://suttacentral.net/iti1.2#3.4">Iti 1.2:3.4</a>',
            "iti",
            ["iti1.2:3"],
            '<a href="#iti1.2:3.4">Iti 1.2:3.4</a>',
            ['<a href="https://suttacentral.net/iti1.2#3.4">Iti 1.2:3.4</a>'],
        ),
        (
            '<a href="https://suttacentral.net/iti1.2/en/sujato#3.4">Iti 1.2:3.4</a>',
            "iti",
            ["iti1.2:3"],
            '<a href="#iti1.2:3.4">Iti 1.2:3.4</a>',
            ['<a href="https://suttacentral.net/iti1.2/en/sujato#3.4">Iti 1.2:3.4</a>'],
        ),
        # absolute links
        (
            '<a href="/snp1.1-2#2">Snp 1:1</a>',
            "mn",
            ["dummy"],
            '<a class="external-link" href="https://suttacentral.net/snp1.1-2#2">Snp 1:1</a>',
            [],
        ),
        (
            '<a href="snp1.1-2#2">Snp 1:1</a>',
            "mn",
            ["dummy"],
            '<a class="external-link" href="https://suttacentral.net/snp1.1-2#2">Snp 1:1</a>',
            [],
        ),
        (
            '<a href="/an1#2-2">AN 1:2-2</a>',
            "dn",
            ["dummy"],
            '<a class="external-link" href="https://suttacentral.net/an1#2-2">AN 1:2-2</a>',
            [],
        ),
        (
            '<a href="https://suttacentral.net/iti1.2#3.4">Iti 1.2:3.4</a>',
            "snp",
            ["dummy"],
            '<a class="external-link" href="https://suttacentral.net/iti1.2#3.4">Iti 1.2:3.4</a>',
            [],
        ),
        (
            '<a href="https://suttacentral.net/iti1.2/en/sujato#3.4">Iti 1.2:3.4</a>',
            "an",
            ["dummy"],
            '<a class="external-link" href="https://suttacentral.net/iti1.2/en/sujato#3.4">Iti 1.2:3.4</a>',
            [],
        ),
        # links that should not be modified
        ('<a href="#snp1">Snp 1</a>', "snp", ["snp1"], '<a href="#snp1">Snp 1</a>', []),
        ('<a href="#item1">Test</a>', "snp", ["snp1"], '<a href="#item1">Test</a>', []),
        # links that should not be modified and returned in mismatches
        (
            '<a href="#snp-wrongid">Snp 1</a>',
            "snp",
            ["snp"],
            '<a href="#snp-wrongid">Snp 1</a>',
            ['<a href="#snp-wrongid">Snp 1</a>'],
        ),
    ],
)
def test_should_return_processed_links(
    html: str, acronym: str, mainmatter_uids: list[str], expected_link: str, expected_mismatches: list[str]
) -> None:
    pattern = RELATIVE_LINKS_PATTERN.format(acronym=acronym)
    assert process_links(html, pattern, mainmatter_uids, acronym) == (expected_link, expected_mismatches)


@pytest.mark.parametrize(
    "acronym, name, root_name, type, uid, mainmatter, exception",
    [
        # correct segments, should not raise
        (
            "",
            "Test Name",
            "Test Root Name",
            "branch",
            "an1.1",
            {},
            False,
        ),
        (
            "an1.1",
            "Test Name",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h1>{}</h1>"}},
            False,
        ),
        # incorrect segments which should raise exception
        (
            "",
            "",
            "Test Root Name",
            "branch",
            "an1.1",
            {},
            True,
        ),
        (
            "",
            "Test Name",
            "",
            "branch",
            "an1.1",
            {},
            True,
        ),
        (
            "",
            "Test Name",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h1>{}</h1>"}},
            True,
        ),
        (
            "an1.1",
            "",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h1>{}</h1>"}},
            True,
        ),
        (
            "an1.1",
            "Test Name",
            "",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h1>{}</h1>"}},
            True,
        ),
        (
            "an1.1",
            "Test Name",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": ""}, "markup": {"an1.1:0.3": "<h1>{}</h1>"}},
            True,
        ),
        (
            "an1.1",
            "Test Name",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h1>{}</h1>", "an1.1:1.1": "<h1>{}</h1>"}},
            True,
        ),
        (
            "an1.1",
            "Test Name",
            "Test Root Name",
            "leaf",
            "an1.1",
            {"main_text": {"an1.1:0.3": "Title"}, "markup": {"an1.1:0.3": "<h2>{}</h2>"}},
            True,
        ),
    ],
)
def test_validate_node(acronym, name, root_name, type, uid, mainmatter, exception):
    node_details = NodeDetails(
        main_text=mainmatter["main_text"] if "main_text" in mainmatter else {},
        markup=mainmatter["markup"] if "markup" in mainmatter else {},
    )
    node = Node(
        acronym=acronym,
        name=name,
        root_name=root_name,
        type=type,
        uid=uid,
        mainmatter=node_details,
    )
    try:
        validate_node(node)
    except SystemExit:
        assert exception
