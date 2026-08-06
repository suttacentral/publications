import re
import subprocess
from pathlib import Path


CJK_TEMPLATE = Path("/app/sutta_publisher/templates/tex/shared/cjk-template.tex")


def compile_cjk_fixture(
    tmp_path: Path,
    body: str,
    *,
    name: str = "chinese-typesetting",
    use_cjk: bool = True,
) -> str:
    cjk_config = CJK_TEMPLATE.read_text() if use_cjk else ""
    tex_file = tmp_path / f"{name}.tex"
    tex_file.write_text(
        "\n".join(
            [
                r"\documentclass[12pt]{book}",
                r"\usepackage[paperwidth=5.8in,paperheight=8.7in,margin=.8in]{geometry}",
                r"\usepackage{fontspec}",
                r"\setmainfont{Arno Pro}",
                cjk_config,
                r"\begin{document}",
                body,
                r"\end{document}",
            ]
        )
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
    assert result.returncode == 0, result.stdout + result.stderr
    return (tmp_path / f"{name}.log").read_text()


def extract_western_typography_width(log: str) -> str:
    match = re.search(r"WESTERN-TYPOGRAPHY-WIDTH=([^\s]+)", log)
    assert match is not None
    return match.group(1)


def test_noto_serif_cjk_tc_is_available() -> None:
    result = subprocess.run(
        ["fc-match", "--format=%{family}", "Noto Serif CJK TC"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.split(",", 1)[0] == "Noto Serif CJK TC"


def test_chinese_footnote_uses_noto_and_wraps(tmp_path: Path) -> None:
    log = compile_cjk_fixture(
        tmp_path,
        r"Text\footnote{Sarvāstivāda Vinaya, fascicle 42: \langlzh{若比丘尼有漏心，聽漏心男子髮際以下至腕膝以上却衣，順摩、逆摩、牽推、按掐、抱上、抱下，是比丘尼得波羅夷不共住。}}",
    )
    assert "Overfull \\hbox" not in log
    assert "NotoSerifCJKtc-Regular" in log
    assert "HaranoAji" not in log


def test_chinese_typesetting_preserves_western_punctuation(tmp_path: Path) -> None:
    body = r"""
\setbox0=\hbox{Rules 1–4; rules 91–93; dash—without spaces; ellipsis…within text.}
\typeout{WESTERN-TYPOGRAPHY-WIDTH=\the\wd0}
\box0
""".strip()
    configured_log = compile_cjk_fixture(
        tmp_path,
        body,
        name="configured-western-typography",
    )
    baseline_log = compile_cjk_fixture(
        tmp_path,
        body,
        name="baseline-western-typography",
        use_cjk=False,
    )
    assert "HaranoAji" not in configured_log
    assert extract_western_typography_width(configured_log) == extract_western_typography_width(baseline_log)
