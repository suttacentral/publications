from sutta_publisher.run import fib


def test_should_do_dummy_check():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
