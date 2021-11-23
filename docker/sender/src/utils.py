import time
import traceback
import sys
import os
import functools
import logging

from datetime import datetime as dt

# ----------------------------------------------------------------------------------------------------------------------
import db
from models import GentlemanInfo

log_file = "./log/logfile.log"
log_level = logging.INFO
logging.basicConfig(
    level=log_level, filename=log_file, filemode="a+", format="%(asctime)-15s %(levelname)-8s %(message)s"
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


# ----------------------------------------------------------------------------------------------------------------------
class Screener:
    screenshots_queue = []
    base_dir = './screenshots/'

    @classmethod
    def push_screen(cls, driver):
        path = f"{cls.base_dir}{dt.now().strftime('%Y-%m-%d_%H%M%S')}.png"
        driver.get_screenshot_as_file(path)
        cls.screenshots_queue.append(path)

    @classmethod
    def pop_screen(cls):
        path = cls.screenshots_queue.pop()
        os.remove(path)


# ----------------------------------------------------------------------------------------------------------------------
def populate_priorities():
    with open('mens_prio.txt') as f:
        profile_ids = [int(line.strip()) for line in f.read().split('\n') if line]

    for profile_id in profile_ids:
        if db.get_gentleman_info_by_profile_id(profile_id):
            db.update_gentleman_info(profile_id, priority=1)
            print(f'Updated priority for {profile_id}')
        else:
            gentleman_info = GentlemanInfo(
                profile_id=profile_id,
                priority=1,
            )
            db.put_gentleman_info(gentleman_info)
            print(f'Created new record for {profile_id}')
