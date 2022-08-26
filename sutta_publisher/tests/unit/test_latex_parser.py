from unittest import mock

import pytest
from bs4 import BeautifulSoup
from pylatex import Document, NoEscape

from sutta_publisher.edition_parsers.latex import LatexEdition


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
        ("<p id='ab1.2:3.4'>Test</p>", "\\mnum{3.4}Test"),
        ("<p class='uddana-intro' id='ab1.2:3.4'>Test</p>", "\\scuddanaintro{\\mnum{3.4}Test}"),
        (
            "<p class='uddana-intro' id='ab1.2:3.4'>Test</p><p>Sibling</p>",
            "\\scuddanaintro{\\mnum{3.4}Test}\n\n",
        ),
        ("<span>Test</span>", "Test"),
        ("<span class='uddana-intro'>Test</span>", "\\scuddanaintro{Test}"),
        ("<span class='blurb-item acronym'>Acronym</span>", "Acronym: "),
        (
            "<span class='blurb-item root-title'>Mūlapariyāyasutta</span>",
            "— \\textit{\\textsanskrit{Mūlapariyāyasutta}}",
        ),
        (
            "<span class='blurb-item root-title'>Not pali</span>",
            "— \\textit{\\textsanskrit{Not pali}}",
        ),
        (
            "<test_tag><span class='blurb-item acronym'>Acronym</span><span class='blurb-item translated-title'>Translated Title </span><span class='blurb-item root-title'>Mūlapariyāyasutta</span></test_tag>",
            "Acronym: Translated Title — \\textit{\\textsanskrit{Mūlapariyāyasutta}}",
        ),
        ("<blockquote class='gatha'>Test</blockqoute>", "\\begin{verse}%\nTest%\n\\end{verse}\n"),
        ("<blockquote>Test</blockqoute>", "\\begin{quotation}%\nTest%\n\\end{quotation}\n"),
        ("<br>", NoEscape(r"\\") + NoEscape("\n")),
        ("<b>Test</b>", "\\textbf{Test}"),
        ("<em>Test</em>", "\\emph{Test}"),
        ("<i lang='lzh'>Test</i>", "\\langlzh{Test}"),
        ("<a role='doc-noteref' href=''>1</a>", "\\footnote{Note}"),
        (
            "<h3 class='sutta-title heading'><span class='sutta-heading acronym'>Acronym</span><span class='sutta-heading translated-title'>Name</span><span class='sutta-heading root-title'>Mūlapariyāyasutta</span></h3>",
            "\\section*{\\setstretch{.85}\\centering{\\normalsize Acronym}\\\\*Name\\\\*{\\vspace*{-.1em}\itshape\\normalsize Mūlapariyāyasutta}}\n\\addcontentsline{toc}{section}{Acronym: Name — {\itshape Mūlapariyāyasutta}}\n\\markboth{Name}{Mūlapariyāyasutta}\n\\extramarks{Acronym}{Acronym}",
        ),
        (
            "<h3 class='sutta-title heading'><span class='sutta-heading acronym'>Acronym</span><span class='sutta-heading translated-title'>Name</span><span class='sutta-heading root-title'>Not pali</span></h3>",
            "\\section*{\\setstretch{.85}\\centering{\\normalsize Acronym}\\\\*Name\\\\*{\\vspace*{-.1em}\itshape\\normalsize Not pali}}\n\\addcontentsline{toc}{section}{Acronym: Name — {\itshape Not pali}}\n\\markboth{Name}{Not pali}\n\\extramarks{Acronym}{Acronym}",
        ),
        (
            "<h3 class='range-title heading'><span class='sutta-heading acronym'>Acronym</span><span class='sutta-heading translated-title'>Name</span><span class='sutta-heading root-title'>Mūlapariyāyasutta</span></h1>",
            "\\section*{\\setstretch{.85}\\centering{\\normalsize Acronym}\\\\*Name\\\\*{\\vspace*{-.1em}\itshape\\normalsize Mūlapariyāyasutta}}\n\\addcontentsline{toc}{section}{Acronym: Name — {\itshape Mūlapariyāyasutta}}\n\\markboth{Name}{Mūlapariyāyasutta}\n\\extramarks{Acronym}{Acronym}",
        ),
        (
            "<h1>Chapter</h1>",
            "\\chapter*{Chapter}\n\\addcontentsline{toc}{chapter}{Chapter}\n\\markboth{Chapter}{Chapter}\n",
        ),
        ("<h2>Section</h2>", "\\section*{Section}\n"),
        ("<h3>Subsection</h3>", "\\subsection*{Subsection}\n"),
        ("<h4>Subsubsection</h4>", "\\subsubsection*{Subsubsection}\n"),
        ("<h5>Paragraph</h5>", "\\paragraph*{Paragraph}\n"),
        ("<h6>Subparagraph</h5>", "\\subparagraph*{Subparagraph}\n"),
        ("<section id='main-toc'>Test</section>", "\\tableofcontents"),
        ("<section class='secondary-toc'>Test</section>", ""),
        (
            "<article class='epigraph'><blockquote class='epigraph-text'><p>Test</p></blockquote><p class='epigraph-attribution'><span class='epigraph-translated-title'>Name<span><span class='epigraph-root-title'>Mūlapariyāyasutta</span><span class='epigraph-reference'>Acronym</span></p></article>",
            "\\newpage\n\n\\vspace*{\\fill}\n\n\\begin{center}\n\\epigraph{Test}{\\vspace*{.5em}\\epigraphTranslatedTitle{Name\\textsanskrit{Mūlapariyāyasutta}Acronym} \\epigraphRootTitle{\\textsanskrit{Mūlapariyāyasutta}}\\\\\\epigraphReference{Acronym}}\n\\end{center}\n\n\\vspace*{2in}\n\n\\vspace*{\\fill}\n\n\\setlength{\\parindent}{1em}",
        ),
        ("<ul><li>Test 1</li></ul>", "\\begin{itemize}%\n\\item Test 1%\n\\end{itemize}\n"),
        ("<ol><li>Test 1</li></ol>", "\\begin{enumerate}%\n\\item Test 1%\n\\end{enumerate}\n"),
        ("<ol><li>Test 1<ul><li>Test 2</li></ul></li></ol>", "\\begin{enumerate}%\n\\item Test 1\\begin{itemize}%\n\\item Test 2%\n\\end{itemize}\n%\n\\end{enumerate}\n"),
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
        ("<i lang='pli'>Mūlapariyāyasutta</i>", "\\textit{\\textsanskrit{Mūlapariyāyasutta}}"),
        ("<test>Test & test _ test</test>", "Test \\& test \\_ test"),
    ],
)
def test_process_tag(doc, latex_edition, html, expected):
    tag = BeautifulSoup(html, "lxml").find("body").next_element
    latex_edition.endnotes = ["Note"]
    latex_edition.sutta_depth = 3
    assert latex_edition._process_tag(doc=doc, tag=tag) == expected
