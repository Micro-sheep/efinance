import sys
import threading

import requests
from rich.console import Console

from ..config import SHOW_TICKFLOW_PROMPT

TICKFLOW_URL = "https://tickflow.org?utm_source=efinance"

_tickflow_after_traceback = threading.local()
_ipython_tickflow_shown = False


def is_connection_error_show_tickflow(exc: requests.exceptions.ConnectionError) -> bool:
    msg = str(exc).lower()
    return "max retries exceeded" in msg or "remote end closed connection" in msg


def _print_tickflow_prompt():
    console = Console()
    console.print()
    console.print(
        "[bold red]网络连接异常[/bold red]，可尝试使用 [link={}]TickFlow[/link] 获取更稳定的数据。".format(
            TICKFLOW_URL
        )
    )
    console.print("  → {}".format(TICKFLOW_URL))
    console.print()


_original_excepthook = sys.excepthook


def _excepthook(exc_type, exc_value, tb):
    _original_excepthook(exc_type, exc_value, tb)
    if (
        exc_type is requests.exceptions.ConnectionError
        and SHOW_TICKFLOW_PROMPT
        and exc_value is not None
        and is_connection_error_show_tickflow(exc_value)
    ):
        _print_tickflow_prompt()


def _install_excepthook():
    if sys.excepthook is not _excepthook:
        global _original_excepthook
        _original_excepthook = sys.excepthook
        sys.excepthook = _excepthook


def _install_ipython_exc():
    try:
        from IPython import get_ipython

        ip = get_ipython()
    except Exception:
        return
    if ip is None:
        return

    def _ipython_maybe_show_tickflow():
        global _ipython_tickflow_shown
        if _ipython_tickflow_shown:
            return
        if not SHOW_TICKFLOW_PROMPT:
            return
        exc = getattr(sys, "last_value", None)
        if (
            exc is not None
            and isinstance(exc, requests.exceptions.ConnectionError)
            and is_connection_error_show_tickflow(exc)
        ):
            _ipython_tickflow_shown = True
            _print_tickflow_prompt()

    def pre_execute():
        global _ipython_tickflow_shown
        _ipython_tickflow_shown = False

    def post_run_cell(result):
        if result.error_in_exec is not None:
            _tickflow_after_traceback.show = False
            _ipython_maybe_show_tickflow()

    def post_execute():
        if getattr(_tickflow_after_traceback, "show", False):
            _tickflow_after_traceback.show = False
            _ipython_maybe_show_tickflow()

    ip.events.register("pre_execute", pre_execute)
    ip.events.register("post_run_cell", post_run_cell)
    ip.events.register("post_execute", post_execute)


class CustomedSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", 180)
        try:
            return super(CustomedSession, self).request(*args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            if SHOW_TICKFLOW_PROMPT and is_connection_error_show_tickflow(e):
                _tickflow_after_traceback.show = True
            raise


session = CustomedSession()

_install_excepthook()
_install_ipython_exc()
