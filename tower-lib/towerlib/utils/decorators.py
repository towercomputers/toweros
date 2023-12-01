import logging
import time
from datetime import timedelta

from yaspin import yaspin
from yaspin.spinners import Spinners
from rich import print as rich_print

from towerlib.utils.shell import sh_sudo

logger = logging.getLogger('tower')

def exec_task(function, sudo, *args, **kwargs):
    if sudo:
        with sh_sudo(password="", _with=True):
            return function(*args, **kwargs)
    else:
        return function(*args, **kwargs)

def get_duration_text(start_time, timer_message, message=""):
    duration = timedelta(seconds=time.time() - start_time)
    if duration.seconds > 0:
        seconds = duration.seconds % 60
        str_duration = f"{seconds} second{'s' if seconds > 1 else ''}"
        if duration.seconds > 60:
            minutes = duration.seconds // 60
            str_duration = f"{minutes} minute{'s' if minutes > 1 else ''} {str_duration}"
        if message != "":
            return f"{message} {timer_message.format(str_duration)}"
        return timer_message.format(str_duration)
    return message

def clitask(message=None, timer=True, timer_message="Done in {0}", sudo=False, task_parent=False):
    def decorator(function):
        def new_function(*args, **kwargs):
            if timer:
                start_time = time.time()
            args_values = list(args) + list(kwargs.values())
            formated_message = message.format(*args_values)
            if task_parent:
                rich_print(f"[bold blue]{formated_message}")
                ret = exec_task(function, sudo, *args, **kwargs)
                rich_print(f"[bold green]{get_duration_text(start_time, timer_message)}")
            else:
                with yaspin(Spinners.bouncingBar, text=formated_message, timer=timer) as spinner:
                    ret = exec_task(function, sudo, *args, **kwargs)
                    #spinner.text = get_duration_text(start_time, timer_message, formated_message)
                    spinner.ok("[OK]")
            return ret
        return new_function
    return decorator
