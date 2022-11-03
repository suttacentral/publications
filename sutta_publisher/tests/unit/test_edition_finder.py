from unittest import mock

import pytest

from sutta_publisher.shared.edition_finder import _get_match, get_all_uids, get_mapping


@pytest.mark.parametrize(
    "text_uid, expected",
    [
        ("dhp", ["dhp"]),
        ("mn", ["mn"]),
        (
            "pli-tv-vi",
            [
                "pli-tv-vi",
                "pli-tv-bu-vb",
                "pli-tv-bi-vb",
                "pli-tv-kd",
                "pli-tv-pvr",
                "pli-tv-bu-pm",
                "pli-tv-bi-pm",
            ],
        ),
    ],
)
def test_get_all_uids(super_tree, text_uid, expected) -> None:
    assert get_all_uids(super_tree, text_uid) == expected


@mock.patch("sutta_publisher.shared.edition_finder.get_super_tree")
def test_get_mapping(mock_tree, super_tree, editions, publications) -> None:
    mock_tree.return_value = super_tree
    assert get_mapping(editions) == publications


@pytest.mark.parametrize(
    "filename, expected",
    [
        (
            [
                "a/sc_bilara_data/translation/en/brahmali/vinaya/pli-tv-bi-vb/pli-tv-bi-vb-np/pli-tv-bi-vb-np10_translation-en-brahmali.json"
            ],
            [False, True],
        ),
        (["a/sc_bilara_data/comment/en/sujato/sutta/kn/snp/vagga1/snp1.12_comment-en-sujato.json"], [True, False]),
        (
            ["a/sc_bilara_data/html/pli/ms/vinaya/pli-tv-bu-vb/pli-tv-bu-vb-np/pli-tv-bu-vb-np10_html.json"],
            [False, True],
        ),
        (["a/sc_bilara_data/variant/pli/ms/sutta/kn/snp/vagga3/snp3.10_variant-pli-ms.json"], [True, False]),
        (["a/sc_bilara_data/reference/pli/ms/vinaya/pli-tv-kd/pli-tv-kd12_reference.json"], [False, True]),
        (
            ["a/sc_bilara_data/translation/en/brahmali/vinaya/pli-tv-pvr/pli-tv-pvr1.11_translation-en-brahmali.json"],
            [False, True],
        ),
        (["a/sc_bilara_data/root/en/blurb/snp-blurbs_root-en.json"], [True, False]),
        (
            ["a/sc_bilara_data/translation/en/sujato/sutta/kn/snp/vagga4/snp4.16_translation-en-sujato.json"],
            [True, False],
        ),
        (
            [
                "a/translation/en/brahmali/vinaya/pli-tv-bi-wz/pli-tv-bi-wz-np/pli-tv-bi-wz-np10_translation-en-brahmali.json"
            ],
            [False, False],
        ),
        (["a/sc_bilara_data/comment/de/sujato/sutta/kn/mn/mn1.12_comment-en-sujato.json"], [False, False]),
        (
            ["a/sc_bilara_data/html_test/pli/ms/vinaya/pli-tv-bu-vb/pli-tv-bu-vb-np/pli-tv-bu-vb-np10_html.json"],
            [False, False],
        ),
        (["a/sc_bilara_data/variant/pli/ms/sutta/kn/vagga3/snp3.10_variant-pli-ms.json"], [False, False]),
        (["a/sc_bilara_data/pli/ms/vinaya/pli-tv-kd/pli-tv-kd12_reference.json"], [False, False]),
        (
            ["a/sc_bilara_data/translation/de/brahmali/vinaya/pli-tv-pvr/pli-tv-pvr1.11_translation-en-brahmali.json"],
            [False, False],
        ),
        (["a/sc_bilara_data/root/en/blurb/mn-blurbs_root-en.json"], [False, False]),
        (
            ["a/sc_bilara_data/translation/en/brahmali/sutta/kn/snp/vagga4/snp4.16_translation-en-sujato.json"],
            [False, False],
        ),
    ],
)
def test_get_match(filename, expected, publications) -> None:
    patterns = [
        {"any": ("/_publication/", "/comment/"), "all": ("/{lang_iso}/", "/{creator}/", "/{uid}/")},
        {"any": ("/html/", "/reference/", "/variant/"), "all": ("/{uid}/",)},
        {"all": ("/root/", "/blurb/", "/{lang_iso}/", "/{uid}-")},
        {"any": ("/{uid}/", "/{uid}-"), "all": ("/translation/", "/{lang_iso}/", "/{creator}/")},
    ]

    _publications = sorted(list(publications), key=lambda x: x[0])
    for idx, pub in enumerate(_publications):
        assert _get_match(pub, filename, patterns) == expected[idx]
