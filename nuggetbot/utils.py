from datetime import datetime, timedelta
import inspect


def get_next(**kwargs):
    today = datetime.now()
    delta = timedelta(**kwargs)
    return today + delta

class Response:
    def __init__(self, content="", reply=True, delete_after=None, embed=None):
        self.content = content
        self.embed = embed
        self.reply = reply
        self.delete_after = delete_after

def _get_variable(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack