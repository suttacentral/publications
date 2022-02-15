from sutta_publisher.ingester.tsv_parser import TsvParser


def test_should_generate_valid_html_string(get_file_path, get_data):
    test_tsv = get_file_path("dn.tsv")

    parser = TsvParser(test_tsv)
    html = parser.parse_input()
    expected_html = get_data("test_output.html")
    assert html == expected_html
