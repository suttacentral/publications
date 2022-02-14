from io import StringIO

from sutta_publisher.ingester.tsv_parser import TsvParser


def test_should_generate_valid_html_string():
    input_tsv = StringIO(
        """
segment_id			translation-en-sujato				html	reference
dn1:0.1			Long Discourses 1 				<article id='dn1'><header><ul><li class='division'>{}</li></ul>
dn1:0.2			The Prime Net 				<h1 class='sutta-title'>{}</h1></header>
dn1:0.3			1. Talk on Wanderers 				<h2>{}</h2>
dn1:1.1.1			So I have heard. 				<p><span class='evam'>{}</span>	bj7.2, cck9.1, csp1ed6.1, csp2ed6.1, dr9.1, km14.1, km14.2, lv1.1, lv1.2, mc9.1, ms6D_2, msdiv1, ndp6.3, pts-cs1.1, pts-vp-pli1.1, sya9.1, vri1.1, vri1.2
    """
    )

    expected_html = """
<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Long Discourses</title>
<style>
</style>
</head>
<body>

<article id='dn1'><header><ul><li class='division'>Long Discourses 1 <a id='dn1:0.1'></a></li></ul>
<h1 class='sutta-title'>The Prime Net <a id='dn1:0.2'></a></h1></header>
<h2>1. Talk on Wanderers <a id='dn1:0.3'></a></h2>
<p><span class='evam'><a class='bj' id='bj7.2'>BJ 7.2</a>So I have heard. <a id='dn1:1.1.1'></a></span>
</body>
</html>
        """

    parser = TsvParser(input_tsv)
    html = parser.parse_input()
    assert html == expected_html
