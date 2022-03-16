import json
from pathlib import Path
from typing import Any

import pytest

from sutta_publisher.edition_parsers.base import EditionParser
from sutta_publisher.shared.value_objects.edition_config import EditionConfig
from sutta_publisher.shared.value_objects.edition_data import EditionData, MainMatter, MainMatterInfo, VolumeData

PAYLOADS_PATH = Path("/app/sutta_publisher/shared/example_payloads/")


@pytest.fixture
def list_of_all_refs() -> list[str]:
    return [
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


@pytest.fixture
def example_data_payload() -> list[dict[str, Any]]:
    return json.load(open(PAYLOADS_PATH / "mn-en-sujato_scpub3-ed6-html_2022-02-10-mn.json"))  # type: ignore


@pytest.fixture
def example_config_payload() -> dict[str, Any]:
    return json.load(open(PAYLOADS_PATH / "mn-en-sujato_scpub3-ed6-html_2022-02-10.json"))  # type: ignore


@pytest.fixture
def example_edition_config(example_config_payload: dict[str, Any]) -> EditionConfig:
    return EditionConfig(**example_config_payload)


@pytest.fixture
def single_volume(example_data_payload: list[dict[str, Any]]) -> VolumeData:
    mainmatter_list: list[MainMatterInfo] = []
    for main_matter_info in example_data_payload:
        mainmatter_list.append(MainMatterInfo(**main_matter_info))
    actual_mainmatter = MainMatter(__root__=mainmatter_list)

    return VolumeData(mainmatter=actual_mainmatter, extras={})


@pytest.fixture
def example_edition_data(single_volume: VolumeData) -> EditionData:
    return EditionData([single_volume])


@pytest.fixture
def base_parser(example_edition_config: EditionConfig, example_edition_data: EditionData) -> EditionParser:
    return EditionParser(config=example_edition_config, data=example_edition_data)


def test_should_parse_json_to_html(base_parser: EditionParser) -> None:
    generated_html = base_parser._EditionParser__generate_html()
    assert generated_html is not None

html_head = """
<!DOCTYPE html>
<html>

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Long Discourses</title>
    <style>
        @font-face {
            font-family: 'Source Serif 4 Variable';
            font-weight: 100 900;
            font-style: normal;
            src: url('SourceSerif4Variable-Roman.otf.woff2') format('woff2-variations');
        }

        @font-face {
            font-family: 'Source Serif 4 Variable';
            font-weight: 100 900;
            font-style: italic;
            src: url('SourceSerif4Variable-Italic.otf.woff2') format('woff2-variations');
        }

        @font-face {
            font-family: 'Source Sans 3 VF';
            font-weight: 100 900;
            font-style: normal;
            src: url('SourceSans3VF-Roman.otf.woff2') format('woff2-variations');
        }

        @font-face {
            font-family: 'Source Sans 3 VF';
            font-weight: 100 900;
            font-style: italic;
            src: url('SourceSans3VF-Italic.otf.woff2') format('woff2-variations');
        }

         :root {
            --font-size-small: 0.8rem;
            font-optical-sizing: auto;
        }

        p,
        ul,
        ol,
        dl,
        tr {
            font-size: 16px;
            font-variation-settings: 'opsz', 16;
        }

        main {
            --primary-text-color: black;
            --secondary-text-color: #757575;
            --primary-background-color: white;
            --secondary-background-color: #efefef;
            --border-color: rgba(0, 0, 0, 0.1);
            --link-color: #e60026;
            --font-weight-normal: 400;
            --font-weight-semibold: 600;
            --font-weight-bold: 800;
            --scrollbarBG: rgba(0, 0, 0, .1);
            --thumbBG: rgba(0, 0, 0, .2);
            --umbra-opacity: rgba(0, 0, 0, 0.1);
            --penumbra-opacity: rgba(0, 0, 0, 0.07);
            --ambient-opacity: rgba(0, 0, 0, 0.06);
            --shadow-elevation-1dp: 0px 2px 0px -1px var(--umbra-opacity), 0px 1px 1px 0px var(--penumbra-opacity), 0px 1px 0px 0px var(--ambient-opacity);
            --shadow-elevation-4dp: 0px 2px 4px -1px var(--umbra-opacity), 0px 4px 5px 0px var(--penumbra-opacity), 0px 1px 10px 0px var(--ambient-opacity);
        }

        #toggle:checked~main {
            --primary-text-color: #eee;
            --secondary-text-color: #aaa;
            --primary-background-color: #333;
            --secondary-background-color: #555;
            --border-color: rgba(255, 255, 255, 0.1);
            --link-color: #e6ba00;
            --font-weight-normal: 430;
            --font-weight-semibold: 630;
            --font-weight-bold: 830;
            --scrollbarBG: rgba(0, 0, 0, .1);
            --thumbBG: rgba(0, 0, 0, .2);
        }

        #toggle {
            position: fixed;
            z-index: 2000;
            top: 12px;
            left: 1em;
        }

        #toggle+label {
            font-size: var(--font-size-small);
            position: fixed;
            z-index: 2000;
            top: -4px;
            left: 2.5em;
            color: #777;
        }

        * {
            box-sizing: border-box;
            margin: 0;
        }

        body {
            font-family: 'Source Serif 4 Variable', 'Source Sans 3 VF', serif;
            line-height: 1.5;
            width: 100%;
            height: 100%;
        }

        main {
            font-weight: var(--font-weight-normal);
            width: 100%;
            position: relative;
            margin-top: 0;
            color: var(--primary-text-color);
            background-color: var(--primary-background-color);
        }

        #frontmatter,
        #mainmatter,
        #backmatter {
            max-width: 40em;
            margin: 2em auto;
        }

        article {
            width: 100%;
            padding: 0 0 8em 0;
        }

        #toc,
        label {
            font-family: 'Source Sans 3 VF', sans-serif;
        }

        a {
            text-decoration: none;
            color: var(--link-color);
            overflow-wrap: anywhere;
            white-space: pre;
        }

        a:hover {
            text-decoration: underline;
            text-underline-offset: .09em;
            text-decoration-thickness: from-font;
        }

        .bj,
        .pts-vp-pli,
        .sc-main {
            text-decoration: none;
            font-size: small;
            margin-right: 1ex;
            font-weight: normal;
            color: var(--secondary-text-color);
        }

        .bj:hover,
        .pts-vp-pli:hover,
        .sc-main:hover {
            text-decoration: none;
        }

        article {
            position: relative;
        }

        .sc-main {
            position: absolute;
            left: -8em;
        }

        b,
        strong {
            font-weight: var(--font-weight-bold);
        }

        *+* {
            margin-top: 1em;
        }

        body,
        li,
        ol ul,
        ol ol,
        ul ul,
        dl ul,
        nav ul,
        ol dl,
        ul dl,
        dd,
        dt {
            margin-top: 0;
        }

        ul,
        ol {
            padding-left: 2rem;
        }

        blockquote {
            margin: 1em 1.5em;
        }

        #toc li {
            margin: .5em 0;
        }

        #title-page {
            line-height: 1;
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100vh;
            text-align: center;
            justify-content: space-between;
            align-content: center;
        }

        .title-page-main {
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 80vh;
        }

        .translation_title {
            font-size: 4rem;
            font-variant-caps: all-small-caps;
            margin-top: 8rem;
        }

        .translation_subtitle {
            font-size: 1.5em;
            font-style: italic;
        }

        .author_name {
            font-size: 2em;
            margin-bottom: 8rem;
        }

        .title-page-foot {
            color: var(--link-color);
            height: 20vh;
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            padding: 0 6em;
        }

        #license {
            background-color: var(--secondary-background-color);
            padding: 2em;
            border: 1px solid var(--border-color);
            border-radius: 1em;
        }

        nav {}

        nav ul {
            list-style-type: none
        }

        h1 {
            font-size: 2rem;
            width: 100%;
            margin-bottom: 1em;
            text-align: center;
        }

        h2 {
            font-size: 1.5rem;
        }

        h3 {
            font-size: 1.33rem;
        }

        h4 {
            font-size: 1.25rem;
        }

        h5 {
            font-size: 1rem;
        }

        dl {
            display: grid;
            width: fit-content;
            grid-template-columns: 1fr 6fr;
            align-items: baseline;
            gap: 1em;
        }

        dt {
            font-weight: var(--font-weight-semibold);
        }

        dd {
            margin-left: 2em;
        }

        section+section {
            margin-top: 6rem;
        }
    </style>
</head>
"""

html_tail = """
</body>

</html>"""
