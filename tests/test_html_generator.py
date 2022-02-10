from html_generator.html_generator import _catch_translation_en_column, _reference_to_html, _split_ref_and_number


def test_should_check_creating_html_from_reference():
    assert _reference_to_html(("bj", "7.2")) == "<a class='bj' id='bj7.2'>BJ 7.2</a>"
    assert _reference_to_html(("pts-vp-pli", "14.2")) == "<a class='pts-vp-pli' id='pts-vp-pli14.2'>PTS-VP-PLI 14.2</a>"


def test_should_check_creating_tuple_from_reference():
    assert _split_ref_and_number("bj7.2") == ("bj", "7.2")
    assert _split_ref_and_number("pts-vp-pli14.2") == ("pts-vp-pli", "14.2")
    assert _split_ref_and_number("invalid-ref2.2") is None
    assert _split_ref_and_number("bj") is None


def test_should_check_finding_english_translation_column():
    column_names1 = [
        "segment_id",
        "root-pli-ms",
        "translation-de-sabbamitta",
        "translation-en-sujato",
        "translation-my-my-team",
        "translation-pl-hardao",
        "translation-ru-team",
        "html",
        "reference",
        "variant-pli-ms",
    ]
    column_names2 = [
        "segment_id",
        "translation-de-sabbamitta",
        "html",
    ]
    assert _catch_translation_en_column(column_names1) == "translation-en-sujato"
    assert _catch_translation_en_column(column_names2) is None
