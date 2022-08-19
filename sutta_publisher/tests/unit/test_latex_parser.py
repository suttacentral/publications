from unittest import mock

import pytest
from bs4 import BeautifulSoup
from pylatex import Document, NoEscape

from sutta_publisher.edition_parsers.pdf import LatexEdition


@pytest.fixture()
def doc():
    return Document()


@pytest.fixture()
@mock.patch("sutta_publisher.shared.value_objects.edition_config.EditionConfig.__init__", return_value=None)
@mock.patch("sutta_publisher.shared.value_objects.edition_data.EditionData.__init__", return_value=None)
def latex_edition(config, data):
    return LatexEdition(config, data)


@pytest.mark.parametrize(
    "html, expected",
    [
        ("<p>Test</p>", "Test"),
        ("<p id='ab1.2:3.4'>Test</p>", "\\marginnote[3.4]{3.4}Test"),
        ("<p class='uddana-intro' id='ab1.2:3.4'>Test</p>", "\\scuddanaintro{\\marginnote[3.4]{3.4}Test}"),
        (
            "<p class='uddana-intro' id='ab1.2:3.4'>Test</p><p>Sibling</p>",
            "\\scuddanaintro{\\marginnote[3.4]{3.4}Test}\n\n",
        ),
        ("<span>Test</span>", "Test"),
        ("<span class='uddana-intro'>Test</span>", "\\scuddanaintro{Test}"),
        ("<span class='blurb-item acronym'>Acronym</span>", "Acronym: "),
        ("<span class='blurb-item root-title'>Root Title</span>", "— Root Title"),
        ("<blockquote class='gatha'>Test</blockqoute>", "\\begin{verse}%\nTest%\n\\end{verse}\n"),
        ("<blockquote>Test</blockqoute>", "\\begin{quotation}%\nTest%\n\\end{quotation}\n"),
        ("<br>", NoEscape(r"\\") + NoEscape("\n")),
        ("<b>Test</b>", "\\textbf{Test}"),
        ("<em>Test</em>", "\\emph{Test}"),
        ("<i lang='pli'>Test</i>", "\\langpli{Test}"),
        ("<i lang='lzh'>Test</i>", "\\langlzh{Test}"),
        ("<a role='doc-noteref' href=''>1</a>", "\\footnote{Note}"),
        (
            "<h3 class='sutta-title'><span class='acronym'>Acronym</span><span class='name'>Name</span><span class='root-name'>Root</span></h3>",
            "\\section*{\\setstretch{.85}\\centering{\\normalsize Acronym}\\\\*Name\\\\*{\\vspace*{-.1em}\itshape\\normalsize Root}}\n\\addcontentsline{toc}{section}{Acronym: Name — {\itshape Root}}\n\\markboth{Name}{Root}\n\\extramarks{Acronym}{Acronym}",
        ),
        (
            "<h1 class='range-title'><span class='acronym'>Acronym</span><span class='name'>Name</span><span class='root-name'>Root</span></h1>",
            "\\section*{\\setstretch{.85}\\centering{\\normalsize Acronym}\\\\*Name\\\\*{\\vspace*{-.1em}\itshape\\normalsize Root}}\n\\addcontentsline{toc}{section}{Acronym: Name — {\itshape Root}}\n\\markboth{Name}{Root}\n\\extramarks{Acronym}{Acronym}",
        ),
        ("<h1>Test</h1>", "\\chapter*{Test}\n\\addcontentsline{toc}{chapter}{Test}\n\\markboth{Test}{Test}\n"),
        ("<h2>Test</h2>", "\\section*{Test}\n"),
        ("<section id='main-toc'>Test</section>", "\\tableofcontents"),
        (
            "<article class='epigraph'><blockquote class='epigraph-text'><p>Test</p></blockquote><p class='epigraph-attribution'><span class='epigraph-translated-title'>Name<span><span class='epigraph-root-title'>Root</span><span class='epigraph-reference'>Acronym</span></p></article>",
            "\\newpage\n\n\\vspace*{\\fill}\n\n\\begin{center}\n\\epigraph{Test}{\\vspace*{.5em}\\epigraphTranslatedTitle{NameRootAcronym} \\epigraphRootTitle{Root}\\\\\\epigraphReference{Acronym}}\n\\end{center}\n\n\\vspace*{2in}\n\n\\vspace*{\\fill}\n\n\\setlength{\\parindent}{1em}",
        ),
        ("<ul><li>Test 1</li></ul>", "\\begin{itemize}%\n\\item Test 1%\n\\end{itemize}\n"),
        ("<ol><li>Test 1</li></ol>", "\\begin{enumerate}%\n\\item Test 1%\n\\end{enumerate}\n"),
        (
            "<dl><dt>Topic 1</dt><dd>Item 1</dd></dl>",
            "\\begin{description}%\n\\item[Topic 1] Item 1%\n\\end{description}\n",
        ),
        (
            "<h1 class='section-title'>Test</h1>",
            "\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\nopagecontentsline}\n\\part*{Test}\n\\addcontentsline{toc}{part}{Test}\n\\markboth{}{}\n\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\oldcontentsline}",
        ),
        (
            "<h2 class='section-title'>Test</h1>",
            "\\chapter*{Test}\n\\addcontentsline{toc}{chapter}{Test}\n\\markboth{Test}{Test}\n",
        ),
    ],
)
def test_process_tag(doc, latex_edition, html, expected):
    tag = BeautifulSoup(html, "lxml").find("body").next_element
    latex_edition.endnotes = ["Note"]
    latex_edition.sutta_depth = 3
    assert latex_edition._process_tag(doc=doc, tag=tag) == expected
