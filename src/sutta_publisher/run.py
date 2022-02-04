import logging
from random import randint

log = logging.getLogger(__name__)


def setup_logging() -> None:
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=logging.INFO, format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def fib(n: int) -> int:
    a, b = 1, 1
    for _i in range(n - 1):
        a, b = b, a + b
    return a


def main() -> None:
    setup_logging()
    n = randint(10, 30)  # nosec
    log.debug("Starting crazy calculations...")
    log.info("The %s-th Fibonacci number is %s", n, fib(n))
    log.debug("Script ends here")


if __name__ == "__main__":
    main()
