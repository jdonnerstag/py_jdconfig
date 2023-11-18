#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Package utilities
"""

from dataclasses import dataclass
import logging
from pathlib import Path, WindowsPath
import typing
from abc import ABC
from io import StringIO
from typing import Mapping, Sequence, Optional

if typing.TYPE_CHECKING:
    from .placeholders import Placeholder
    #from .getter_context import GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


def relative_to_cwd(path: Path | str) -> str:
    """Return either the a path relative to cwd or an absolute path"""

    if not isinstance(path, (Path, str)):
        return repr(path)

    path = Path(path).resolve().absolute()
    is_win = isinstance(path, WindowsPath)
    orig = path = str(path)
    cwd = str(Path.cwd())
    if is_win:
        path = path.lower()
        cwd = cwd.lower()

    if path.startswith(cwd):
        orig = "." + orig[len(cwd) :]

    return orig


@dataclass
class Trace:
    """Config Exception Trace Entry"""

    path: tuple[str | int, ...] | None = None
    placeholder: Optional["Placeholder"] = None
    file: str | None = None


def new_trace(ctx: "GetterContext", placeholder: "Placeholder" = None):
    """Create a new Trace or None"""

    if not ctx:
        return None

    filename = None
    # if isinstance(ctx.current_file, "ConfigFile"):
    if type(ctx.current_file).__name__ == "ConfigFile":
        filename = ctx.current_file.file_1

    return Trace(path=ctx.cur_path(), placeholder=placeholder, file=filename)


class ConfigException(Exception):
    """Base class for Config Exceptions"""

    def __init__(self, *args: object, trace: Optional[Trace] = None) -> None:
        super().__init__(*args)

        self.trace = []
        if trace:
            self.trace.append(trace)

    def __str__(self) -> str:
        out = StringIO()
        print(super().__str__(), file=out)

        if self.trace:
            print("Config Trace:", file=out)  # newline

            for i, trace in enumerate(self.trace):
                print(f"{i + 1:2d}: path={trace.path}", file=out)
                print(f"    placeholder={trace.placeholder}", file=out)
                print(f"    file={trace.file}", file=out)

        return out.getvalue()


# pylint: disable=too-few-public-methods
class NonStrSequence(ABC):
    """Avoid having to do `isinstance(x, Sequence) and not isinstance(x, str)` all the time"""

    @classmethod
    def __subclasshook__(cls, C: type):  # pylint: disable=invalid-name
        if (C is str) or (C is bytes):
            return NotImplemented

        return issubclass(C, Sequence)


ContainerType = Mapping | NonStrSequence

DEFAULT = object()
