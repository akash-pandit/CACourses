from contextlib import contextmanager
from logging import Logger, INFO
from time import perf_counter


@contextmanager
def timer(label: str = "Timer", logger: Logger | None = None, level: int = INFO):
    """
    Timer context manager / decorator. Reports duration with either a logger object at the
    given level severity or a print call.
    
    :param label: timer name
    :type label: str
    :param logger: an initialized logging.Logger object. If not present, timer reports with print().
    :type logger: Logger | None
    :param level: severity level for logger if applicable, defaults to logging.INFO (Literal[20]).
    :type level: int
    """
    start = perf_counter()
    msg = f"[{label}] Beginning timer"
    logger.log(level=level, msg=msg) if isinstance(logger, Logger) else print(msg)
    try:
        yield
    finally:
        duration = perf_counter() - start
        msg = f"[{label}] Execution time: {duration:.2f} seconds"
        logger.log(level=level, msg=msg) if isinstance(logger, Logger) else print(msg)
        