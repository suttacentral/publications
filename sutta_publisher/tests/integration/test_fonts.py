import subprocess
from pathlib import Path


def test_noto_serif_cjk_tc_is_available() -> None:
    result = subprocess.run(
        ["fc-match", "--format=%{family}", "Noto Serif CJK TC"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.split(",", 1)[0] == "Noto Serif CJK TC"


def test_chinese_footnote_can_wrap(tmp_path: Path) -> None:
    template = Path("/app/sutta_publisher/templates/tex/shared/preamble-template.tex").read_text()
    assert r"\usepackage{luatexja}" in template

    tex_file = tmp_path / "chinese-footnote.tex"
    tex_file.write_text(
        r"""
\documentclass[12pt]{book}
\usepackage[paperwidth=5.8in,paperheight=8.7in,margin=.8in]{geometry}
\usepackage{fontspec}
\usepackage{luatexja}
\newfontfamily\cjk{Noto Serif CJK TC}
\newcommand*{\langlzh}[1]{\cjk{#1}\normalfont}
\begin{document}
Text\footnote{Sarvāstivāda Vinaya, fascicle 42: \langlzh{若比丘尼有漏心，聽漏心男子髮際以下至腕膝以上却衣，順摩、逆摩、牽推、按掐、抱上、抱下，是比丘尼得波羅夷不共住。}}
\end{document}
""".strip()
    )

    result = subprocess.run(
        [
            "lualatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            f"-output-directory={tmp_path}",
            str(tex_file),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    log = (tmp_path / "chinese-footnote.log").read_text()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Overfull \\hbox" not in log
