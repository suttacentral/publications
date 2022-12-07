from pathlib import Path
from unittest import mock

import pytest
from bs4 import BeautifulSoup

from sutta_publisher.edition_parsers.helper_functions import (
    _filter_refs,
    _flatten_list,
    _reference_to_html,
    _split_ref_and_number,
    fetch_possible_refs,
    generate_html_toc,
    make_absolute_links,
    make_paperback_zip_files,
    process_line,
    validate_node,
)
from sutta_publisher.shared.value_objects.edition_data import Node, NodeDetails
from sutta_publisher.shared.value_objects.parser_objects import ToCHeading


def soup():
    return BeautifulSoup(parser="lxml")


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
            "lorem ipsum ",
            "test note for lorem ipsum",
            "vnp1.9, pts-vp-pli14.2",
            "<p id='dn1:0.1'><a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>lorem ipsum<a href='#note-{number}' id='noteref-{number}' role='doc-noteref' epub:type='noteref'>{number}</a> ",
            ["pts-vp-pli"],
        ),
        (
            "<h1 class='sutta-title'>{}</h1></header>",
            "mn138:0.2",
            "dolor sit. ",
            "test note for dolor sit",
            "invalid_ref, bj7.9",
            "<h1 class='sutta-title'><a class='bj' id='bj7.9'>BJ 7.9</a>dolor sit.<a href='#note-{number}' id='noteref-{number}' role='doc-noteref' epub:type='noteref'>{number}</a> </h1></header>",
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
    "html, expected",
    [
        (
            "<a href='/snp5.13/en/sujato#4.3'>Snp 5.13:4.3</a>",
            "<a href='https://suttacentral.net/snp5.13/en/sujato#4.3'>Snp 5.13:4.3</a>",
        ),
        (
            "<a href='/mn-abcdef'>MN 1</a>",
            "<a href='https://suttacentral.net/mn-abcdef'>MN 1</a>",
        ),
        (
            "<a href='https://suttacentral.net/iti1.2#3.4'>Iti 1.2:3.4</a>",
            "<a href='https://suttacentral.net/iti1.2#3.4'>Iti 1.2:3.4</a>",
        ),
        (
            "<a href='https://test.com/some-test-link'>Iti 1.2:3.4</a>",
            "<a href='https://test.com/some-test-link'>Iti 1.2:3.4</a>",
        ),
        (
            "<a href='#mn1'>MN1</a>",
            "<a href='#mn1'>MN1</a>",
        ),
    ],
)
def test_should_return_html_with_processed_link(html: str, expected: str) -> None:
    assert make_absolute_links(html) == expected


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
            "",
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
def test_validate_node(
    acronym: str,
    name: str,
    root_name: str,
    type: str,
    uid: str,
    mainmatter: dict[str, str],
    exception: bool,
):
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


@pytest.mark.parametrize(
    "headings, expected",
    [
        (
            [
                ToCHeading(
                    acronym=None,
                    depth=1,
                    name="Foo1",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo1">Foo1</h1>'),
                    type="frontmatter",
                    uid="foo1",
                ),
                ToCHeading(
                    acronym=None,
                    depth=1,
                    name="Foo2",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo2">Foo2</h1>'),
                    type="branch",
                    uid="foo2",
                ),
                ToCHeading(
                    acronym=None,
                    depth=2,
                    name="Foo3",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo3">Foo3</h1>'),
                    type="branch",
                    uid="foo3",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo4",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo4">Foo4</h1>'),
                    type="branch",
                    uid="foo4",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo5",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo5">Foo5</h1>'),
                    type="branch",
                    uid="foo5",
                ),
                ToCHeading(
                    acronym=None,
                    depth=2,
                    name="Foo6",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo6">Foo6</h1>'),
                    type="branch",
                    uid="foo6",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo7",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo7">Foo7</h1>'),
                    type="branch",
                    uid="foo7",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo8",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo8">Foo8</h1>'),
                    type="branch",
                    uid="foo8",
                ),
                ToCHeading(
                    acronym=None,
                    depth=1,
                    name="Foo9",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo9">Foo9</h1>'),
                    type="backmatter",
                    uid="foo9",
                ),
            ],
            "<ul><li><a href='#foo1'>Foo1</a></li><li><a href='#foo2'>Foo2</a><ul><li><a href='#foo3'>Foo3</a><ul><li><a href='#foo4'>Foo4</a></li><li><a href='#foo5'>Foo5</a></li></ul></li><li><a href='#foo6'>Foo6</a><ul><li><a href='#foo7'>Foo7</a></li><li><a href='#foo8'>Foo8</a></li></ul></li></ul></li><li><a href='#foo9'>Foo9</a></li></ul>",
        ),
        (
            [
                ToCHeading(
                    acronym=None,
                    depth=1,
                    name="Foo1",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo1">Foo1</h1>'),
                    type="frontmatter",
                    uid="foo1",
                ),
                ToCHeading(
                    acronym=None,
                    depth=1,
                    name="Foo2",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo2">Foo2</h1>'),
                    type="branch",
                    uid="foo2",
                ),
                ToCHeading(
                    acronym=None,
                    depth=2,
                    name="Foo3",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo3">Foo3</h1>'),
                    type="branch",
                    uid="foo3",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo4",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo4">Foo4</h1>'),
                    type="branch",
                    uid="foo4",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo5",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo5">Foo5</h1>'),
                    type="branch",
                    uid="foo5",
                ),
                ToCHeading(
                    acronym=None,
                    depth=2,
                    name="Foo6",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo6">Foo6</h1>'),
                    type="branch",
                    uid="foo6",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo7",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo7">Foo7</h1>'),
                    type="branch",
                    uid="foo7",
                ),
                ToCHeading(
                    acronym=None,
                    depth=3,
                    name="Foo8",
                    root_name=None,
                    tag=soup().new_tag('<h1 id="foo8">Foo8</h1>'),
                    type="branch",
                    uid="foo8",
                ),
            ],
            "<ul><li><a href='#foo1'>Foo1</a></li><li><a href='#foo2'>Foo2</a><ul><li><a href='#foo3'>Foo3</a><ul><li><a href='#foo4'>Foo4</a></li><li><a href='#foo5'>Foo5</a></li></ul></li><li><a href='#foo6'>Foo6</a><ul><li><a href='#foo7'>Foo7</a></li><li><a href='#foo8'>Foo8</a></li></ul></li></ul></li></ul>",
        ),
    ],
)
def test_generate_html_toc(headings, expected):
    assert generate_html_toc(headings) == expected


@pytest.mark.parametrize(
    "file_paths, num_of_volumes, expected",
    [
        (
            [
                "Middle-Discourses-sujato-2022-12-06.tex",
                "Middle-Discourses-sujato-2022-12-06.pdf",
                "Middle-Discourses-sujato-2022-12-06.xmpdata",
                "Middle-Discourses-sujato-2022-12-06-cover.tex",
                "Middle-Discourses-sujato-2022-12-06-cover.pdf",
            ],
            1,
            [
                "Middle-Discourses-sujato-2022-12-06-tex.zip",
                "Middle-Discourses-sujato-2022-12-06.zip",
                "Middle-Discourses-sujato-2022-12-06-cover.zip",
            ],
        ),
        (
            [
                "Middle-Discourses-sujato-2022-12-06-1.tex",
                "Middle-Discourses-sujato-2022-12-06-1.pdf",
                "Middle-Discourses-sujato-2022-12-06-1.xmpdata",
                "Middle-Discourses-sujato-2022-12-06-1-cover.tex",
                "Middle-Discourses-sujato-2022-12-06-1-cover.pdf",
                "Middle-Discourses-sujato-2022-12-06-2.tex",
                "Middle-Discourses-sujato-2022-12-06-2.pdf",
                "Middle-Discourses-sujato-2022-12-06-2.xmpdata",
                "Middle-Discourses-sujato-2022-12-06-2-cover.tex",
                "Middle-Discourses-sujato-2022-12-06-2-cover.pdf",
            ],
            2,
            [
                "Middle-Discourses-sujato-2022-12-06-tex.zip",
                "Middle-Discourses-sujato-2022-12-06.zip",
                "Middle-Discourses-sujato-2022-12-06-cover.zip",
            ],
        ),
    ],
)
def test_make_zip_files_for_paperback_edition(file_paths, num_of_volumes, expected):
    paths = [Path(f"tmp/{_path}") for _path in file_paths]
    expected = [Path(_exp) for _exp in expected]

    with mock.patch("sutta_publisher.edition_parsers.helper_functions._make_zip") as mock_make_zip:
        mock_make_zip.side_effect = lambda filename, paths: Path(filename)
        assert set(make_paperback_zip_files(paths=paths, num_of_volumes=num_of_volumes)) == set(expected)
