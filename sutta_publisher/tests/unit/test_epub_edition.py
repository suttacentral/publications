from types import SimpleNamespace
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from bs4 import BeautifulSoup
from ebooklib.epub import EpubBook, EpubNav, EpubNcx, Link, write_epub

from sutta_publisher.edition_parsers.epub import EpubEdition
from sutta_publisher.shared.value_objects.parser_objects import Volume


@pytest.fixture
def parser():
    parser = EpubEdition.__new__(EpubEdition)
    parser.config = SimpleNamespace(publication=SimpleNamespace(translation_title="Test book"))
    parser.default_style = parser._set_default_style()
    return parser


def test_repeated_matter_classes_preserve_all_chapters_in_epub(parser, tmp_path):
    # scpub8 has six introductions, a glossary with the introduction class,
    # and six appendices. Their shared classes are not unique chapter names.
    volume = Volume(
        frontmatter=[
            f'<article class="introduction"><h1>Introduction {i}</h1>'
            f'<a href="#section-{i}">Section</a><p id="section-{i}">Text {i}</p></article>'
            for i in range(1, 7)
        ],
        backmatter=['<article class="introduction"><h1>Glossary</h1></article>']
        + [f'<article class="appendix"><h1>Appendix {i}</h1></article>' for i in range(1, 7)],
    )
    book = EpubBook()
    book.set_identifier("scpub8-regression")
    book.set_title("Test book")
    book.set_language("en")
    book.add_item(parser.default_style)
    parser._set_frontmatter(book, volume)
    parser._set_backmatter(book, volume)
    book.toc = [Link("introduction.xhtml", "Introduction", "introduction")]
    book.add_item(EpubNav())
    book.add_item(EpubNcx())
    output = tmp_path / "book.epub"
    write_epub(output, book)

    expected_paths = (
        ["introduction.xhtml"]
        + [f"introduction-{i}.xhtml" for i in range(2, 8)]
        + ["appendix.xhtml"]
        + [f"appendix-{i}.xhtml" for i in range(2, 7)]
    )
    with ZipFile(output) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist()))
        package = ElementTree.fromstring(archive.read("EPUB/content.opf"))
        manifest = package.findall("{*}manifest/{*}item")
        hrefs = [item.attrib["href"] for item in manifest]
        assert len(hrefs) == len(set(hrefs))
        by_id = {item.attrib["id"]: item.attrib["href"] for item in manifest}
        spine_paths = [by_id[item.attrib["idref"]] for item in package.findall("{*}spine/{*}itemref")]
        assert spine_paths == expected_paths

        for path, source in zip(expected_paths, volume.frontmatter + volume.backmatter):
            document = BeautifulSoup(archive.read(f"EPUB/{path}"), "xml")
            original = BeautifulSoup(source, "lxml")
            assert list(document.article.stripped_strings) == list(original.article.stripped_strings)
            assert [(tag.name, tag.attrs) for tag in document.article.find_all()] == [
                (tag.name, tag.attrs) for tag in original.article.find_all()
            ]

        nav = ElementTree.fromstring(archive.read("EPUB/nav.xhtml"))
        assert nav.find(".//{*}a").attrib["href"] == "introduction.xhtml"


@pytest.mark.parametrize(
    "names, expected",
    [
        (
            ["introduction", "introduction-2", "introduction"],
            ["introduction.xhtml", "introduction-2.xhtml", "introduction-3.xhtml"],
        ),
        (["preface", "dn1", "endnotes"], ["preface.xhtml", "dn1.xhtml", "endnotes.xhtml"]),
        (["nav"], ["nav-2.xhtml"]),
    ],
)
def test_chapter_paths_do_not_collide(parser, names, expected):
    book = EpubBook()
    html = BeautifulSoup("<article><p>Content</p></article>", "lxml")
    for name in names:
        parser._set_chapter(book, html, name)
    assert [item.file_name for item in book.get_items()] == expected
    assert [item.file_name for item in book.spine] == expected


def test_chapter_names_are_scoped_to_each_book(parser):
    html = BeautifulSoup('<article class="introduction"><p>Content</p></article>', "lxml")
    for _ in range(2):
        book = EpubBook()
        parser._set_chapter(book, html, "introduction")
        assert [item.file_name for item in book.get_items()] == ["introduction.xhtml"]
