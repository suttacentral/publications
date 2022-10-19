from unittest import mock

import pytest
from bs4 import BeautifulSoup
from pylatex import Document, NoEscape

from sutta_publisher.edition_parsers.latex import LatexParser


@pytest.fixture()
def doc():
    return Document()


@pytest.fixture()
@mock.patch("sutta_publisher.shared.value_objects.edition_config.EditionConfig.__init__", return_value=None)
@mock.patch("sutta_publisher.shared.value_objects.edition_data.EditionData.__init__", return_value=None)
def latex_edition(data, config):
    return LatexParser(config, data)


@pytest.mark.parametrize(
    "html, expected",
    [
        # Sutta titles
        (
            "<h3 class='sutta-title heading'><span class='sutta-heading acronym'>Acronym</span><span class='sutta-heading translated-title'>Name</span><span class='sutta-heading root-title'>Mūlapariyāyasutta</span></h3>",
            "\\section*{{\\suttatitleacronym Acronym}{\\suttatitletranslation Name}{\\suttatitleroot Mūlapariyāyasutta}}\n\\addcontentsline{toc}{section}{\\tocacronym{Acronym} \\toctranslation{Name} \\tocroot{Mūlapariyāyasutta}}\n\\markboth{Name}{Mūlapariyāyasutta}\n\\extramarks{Acronym}{Acronym}\n\n",
        ),
        (
            "<h3 class='sutta-title heading'><span class='sutta-heading acronym'>Acronym</span><span class='sutta-heading translated-title'>Name</span><span class='sutta-heading root-title'>Not pali</span></h3>",
            "\\section*{{\\suttatitleacronym Acronym}{\\suttatitletranslation Name}{\\suttatitleroot Not pali}}\n\\addcontentsline{toc}{section}{\\tocacronym{Acronym} \\toctranslation{Name} \\tocroot{Not pali}}\n\\markboth{Name}{Not pali}\n\\extramarks{Acronym}{Acronym}\n\n",
        ),
        # Section titles
        (
            "<h1 class='section-title'>Test</h1>",
            "\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\nopagecontentsline}\n\\part*{Test}\n\\addcontentsline{toc}{part}{Test}\n\\markboth{}{}\n\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\oldcontentsline}\n\n",
        ),
        (
            "<h2 class='section-title'>Test</h2>",
            "\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\nopagecontentsline}\n\\chapter*{Test}\n\\addcontentsline{toc}{chapter}{\\tocchapterline{Test}}\n\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\oldcontentsline}\n\n",
        ),
        (
            "<h3 class='section-title'>Test</h3>",
            "\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\nopagecontentsline}\n\\chapter*{Test}\n\\addcontentsline{toc}{chapter}{\\tocchapterline{Test}}\n\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\oldcontentsline}\n\n",
        ),
        (
            "<h2 class='section-title' id='an3-pathamapannasaka'>Test</h2>",
            "\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\nopagecontentsline}\n\\pannasa{Test}\n\\addcontentsline{toc}{pannasa}{Test}\n\\markboth{}{}\n\\addtocontents{toc}{\\let\\protect\\contentsline\\protect\\oldcontentsline}\n\n",
        ),
        # Subheadings
        (
            "<h4 class='subheading'>Test</h4>",
            "\\subsection*{Test}\n\n",
        ),
        (
            "<h5 class='subheading'>Test</h5>",
            "\\subsubsection*{Test}\n\n",
        ),
        # Headings
        (
            "<h1>Chapter</h1>",
            "\\chapter*{Chapter}\n\\addcontentsline{toc}{chapter}{Chapter}\n\\markboth{Chapter}{Chapter}\n\n",
        ),
        ("<h2>Section</h2>", "\\section*{Section}\n\n"),
        ("<h3>Subsection</h3>", "\\subsection*{Subsection}\n\n"),
        ("<h4>Subsubsection</h4>", "\\subsubsection*{Subsubsection}\n\n"),
        ("<h5>Paragraph</h5>", "\\paragraph*{Paragraph}\n\n"),
        ("<h6>Subparagraph</h5>", "\\subparagraph*{Subparagraph}\n\n"),
        # Foreign script macro
        ("<i lang='lzh'>Test</i>", "\\langlzh{Test}"),
        # <a>
        ("<a role='doc-noteref' href=''>1</a>", "\\footnote{Note}"),
        # <epigraph>
        (
            "<article class='epigraph'><blockquote class='epigraph-text'><p>Test</p></blockquote><p class='epigraph-attribution'><span class='epigraph-translated-title'>Name<span><span class='epigraph-root-title'>Mūlapariyāyasutta</span><span class='epigraph-reference'>Acronym</span></p></article>",
            "\\newpage\n\n\\vspace*{\\fill}\n\n\\begin{center}\n\\epigraph{Test}\n{\n\\epigraphTranslatedTitle{Name\\textsanskrit{Mūlapariyāyasutta}Acronym}\n\\epigraphRootTitle{\\textsanskrit{Mūlapariyāyasutta}}\n\\epigraphReference{Acronym}\n}\n\\end{center}\n\n\\vspace*{2in}\n\n\\vspace*{\\fill}\n\n\\blankpage%\n\n\\setlength{\\parindent}{1em}\n",
        ),
        # <b>
        ("<b>Test</b>", "\\textbf{Test}"),
        # <blockquote>
        ("<blockquote class='gatha'>Test</blockqoute>", "\\begin{verse}%\nTest%\n\\end{verse}\n\n"),
        ("<blockquote>Test</blockqoute>", "\\begin{quotation}%\nTest%\n\\end{quotation}\n\n"),
        # <br>
        ("<br>", NoEscape(r"\\") + NoEscape("\n")),
        # <cite>
        ("<cite>Test</cite>", "\\textit{Test}"),
        # Description list
        (
            "<dl><dt>Topic 1</dt><dd>Item 1</dd></dl>",
            "\\begin{description}%\n\\item[Topic 1] Item 1%\n\\end{description}\n\n",
        ),
        # <em>
        ("<em>Test</em>", "\\emph{Test}"),
        # <hr>
        ("<hr>", "\\thematicbreak\n"),
        # <i>
        ("<i lang='pli'>Mūlapariyāyasutta</i>", "\\textit{\\textsanskrit{Mūlapariyāyasutta}}"),
        # Enjambment <j>
        ("<test>Some text <j>another text </j>more text <br></test>", "Some text \\\\>another text more text \\\\\n"),
        # <ol>
        ("<ol><li>Test 1</li></ol>", "\\begin{enumerate}%\n\\item Test 1%\n\\end{enumerate}\n\n"),
        (
            "<ol><li>Test 1</li><li value='3'>Test 2</li></ol>",
            "\\begin{enumerate}%\n\\item Test 1%\n\\item[3.] Test 2%\n\\end{enumerate}\n\n",
        ),
        (
            "<ol><li>Test 1<ul><li>Test 2</li></ul></li></ol>",
            "\\begin{enumerate}%\n\\item Test 1\\begin{itemize}%\n\\item Test 2%\n\\end{itemize}\n\n%\n\\end{enumerate}\n\n",
        ),
        # <p>
        ("<p>Test</p>", "Test\n\n"),
        ("<p id='ab1.2:3.4'>Test</p>", "Test\\marginnote{3.4} \n\n"),
        ("<p id='ab1.2:3.4'>Test Testing</p>", "Test\\marginnote{3.4} Testing\n\n"),
        ("<p class='uddana-intro' id='ab1.2:3.4'>Test</p>", "\\scuddanaintro{Test}\n\n"),
        (
            "<p class='uddana-intro' id='ab1.2:3.4'>Test</p><p>Sibling</p>",
            "\\scuddanaintro{Test}\n\n",
        ),
        # main-toc
        ("<section id='main-toc'>Test</section>", "\\tableofcontents\n\\newpage\n\\pagestyle{fancy}\n"),
        # secondary-toc
        ("<section class='secondary-toc'>Test</section>", ""),
        # <span>
        ("<span>Test</span>", "Test"),
        ("<span class='uddana-intro'>Test</span>", "\\scuddanaintro{Test}"),
        ("<span class='blurb-item acronym'>Acronym</span>", "Acronym: "),
        (
            "<span class='blurb-item root-title'>Mūlapariyāyasutta</span>",
            "(\\textit{\\textsanskrit{Mūlapariyāyasutta}})",
        ),
        (
            "<span class='blurb-item root-title'>Not pali</span>",
            "(\\textit{\\textsanskrit{Not pali}})",
        ),
        (
            "<test_tag><span class='blurb-item acronym'>Acronym</span><span class='blurb-item translated-title'>Translated Title </span><span class='blurb-item root-title'>Mūlapariyāyasutta</span></test_tag>",
            "Acronym: Translated Title (\\textit{\\textsanskrit{Mūlapariyāyasutta}})",
        ),
        # <ul>
        ("<ul><li>Test 1</li></ul>", "\\begin{itemize}%\n\\item Test 1%\n\\end{itemize}\n\n"),
        # individual characters
        ("<test>Test & test _ test ~ test</test>", "Test \\& test \\_ test \\textasciitilde test"),
    ],
)
def test_process_tag(doc, latex_edition, html, expected):
    tag = BeautifulSoup(html, "lxml").find("body").next_element
    latex_edition.endnotes = ["Note"]
    latex_edition.sutta_depth = 3
    latex_edition.section_type = "section"
    assert latex_edition._process_tag(tag=tag) == expected
