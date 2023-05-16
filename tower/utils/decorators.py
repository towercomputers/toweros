import logging
import time
from datetime import timedelta

import sh

logger = logging.getLogger('tower')

def clitask(message, timer=True, timer_message="Done in {0}", sudo=False):
    def decorator(function):
        def new_function(*args, **kwargs):
            if timer:
                start_time = time.time()
            args_values = list(args) + list(kwargs.values())
            logger.info(message.format(*args_values))
            if sudo:
                with sh.contrib.sudo(password="", _with=True):
                    ret = function(*args, **kwargs)
            else:
                ret = function(*args, **kwargs)
            if timer:
                duration = timedelta(seconds=time.time() - start_time)
                if duration.seconds > 0:
                    seconds = duration.seconds % 60
                    str_duration = f"{seconds} second{'s' if seconds > 1 else ''}"
                    if duration.seconds > 60:
                        minutes = duration.seconds // 60
                        str_duration = f"{minutes} minute{'s' if minutes > 1 else ''} {str_duration}"
                    logger.info(timer_message.format(str_duration))
            return ret
        return new_function
    return decorator