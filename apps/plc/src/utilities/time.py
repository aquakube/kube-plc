import time
import logging
from functools import wraps

from opentelemetry.metrics import Histogram

logger = logging.getLogger()


def profile(debug: bool = False):
    """
    Profiles a functions execution time and records the measurement to the opentelmetry histogram
    """
    def inner(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            """
            The profiler is currently wrapping the readproperty and writeproperty methods of the PLC servient
            args[0] should ref the self object
            args[1] should ref the property name
            """
            start_time = int(time.time() * 1e3)
            result = fn(*args, **kwargs)
            end_time = int(time.time() * 1e3)
            elapsed = end_time - start_time

            if debug:
                logger.debug(f'profile_time elapsed "{fn.__name__}[args={args}, kwargs={kwargs}]": {elapsed} ms')
            else:
                logger.info(f'profile_time elapsed "{fn.__name__}[args={args}, kwargs={kwargs}]": {elapsed} ms')

            histogram: Histogram = get_histogram(*args)
            if histogram:
                histogram.record(elapsed, attributes={"function_name": fn.__name__})

            return result
        return wrapper
    return inner


def get_histogram(*args) -> Histogram | None:
    """ Attempts to acquire the histogram for profiling execution time of a function """
    try:
        return args[0].opentelemetry_client.histogram
    except:
        logger.exception('failed to get histogram for profiler')
