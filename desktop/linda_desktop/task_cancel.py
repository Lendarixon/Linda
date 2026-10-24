"""Request-scoped cooperative cancellation for local tools."""
from contextlib import contextmanager
import threading
_local=threading.local()
class ToolCancelled(Exception):pass
def current():return getattr(_local,'event',None)
def check():
    event=current()
    if event is not None and event.is_set():raise ToolCancelled('cancelled')
@contextmanager
def bind(event):
    previous=current();_local.event=event
    try:check();yield;check()
    finally:_local.event=previous
