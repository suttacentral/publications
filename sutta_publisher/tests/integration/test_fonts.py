import subprocess


def test_noto_serif_cjk_tc_is_available() -> None:
    result = subprocess.run(
        ["fc-match", "--format=%{family}", "Noto Serif CJK TC"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.split(",", 1)[0] == "Noto Serif CJK TC"
