from sutta_publisher.ingester.tsv_parser import TsvParser


def test_should_generate_valid_html_string(get_file_path, get_data):
    test_tsv = get_file_path("dn-sample.tsv")
    expected_html = get_data("test_output.html")
    expected_html = expected_html.rstrip("\n")  # get_data adds newline to the text from file

    parser = TsvParser(test_tsv)
    html = parser.parse_input()
    assert html == expected_html
