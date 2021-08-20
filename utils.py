import time
import traceback
import sys
import functools
import logging

# ----------------------------------------------------------------------------------------------------------------------
log_file = "./logfile.log"
log_level = logging.INFO
logging.basicConfig(
    level=log_level, filename=log_file, filemode="w+", format="%(asctime)-15s %(levelname)-8s %(message)s"
)
logger = logging.getLogger("date_parser")
logger.addHandler(logging.StreamHandler())

# ----------------------------------------------------------------------------------------------------------------------
def call_retrier(
    max_retry_num=7,
    timeout_sec=2 * 60,
    catched_exceptions=(Exception,),
    # propagated_exceptions=(),
    skipped_exceptions=(),
):
    """
    Retry max number of function call if certain exception is raised
    :param func: Function to call
    :param max_retry_num: Maximum number of func call retries
    :param exception_types_str: if one of the given exceptions has been raised
    :return: Wrapped function
    """

    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kw):
            retry_num = 1
            start_time = time.time()
            while True:
                try:
                    result = func(*args, **kw)
                    return result

                except Exception as ex:
                    if not any(isinstance(ex, cls) for cls in catched_exceptions):
                        raise

                    if any(isinstance(ex, cls) for cls in skipped_exceptions):
                        break

                    if retry_num >= max_retry_num:
                        logger.error(
                            "Exception in '%s' (retry #%d of %d): %r" % (func.__name__, retry_num, max_retry_num, ex)
                        )
                        raise

                    time_elapsed = time.time() - start_time
                    if time_elapsed >= timeout_sec:
                        logger.error("Exception in '%s' (timeout %ds): %r" % (func.__name__, timeout_sec, ex))
                        raise

                    time.sleep(min(2 ** retry_num, timeout_sec - time_elapsed))
                    logger.error(
                        "Exception in '%s' (retry #%d of %d): %r" % (func.__name__, retry_num, max_retry_num, ex)
                    )
                    retry_num += 1

        return inner

    return decorator


# ----------------------------------------------------------------------------------------------------------------------
def dump_exception_stack(ex):
    exc_info = sys.exc_info()
    for line in traceback.format_exception(*exc_info):
        logger.error(line)
