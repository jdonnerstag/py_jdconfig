#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Package utilities
"""

import logging
import typing
from abc import ABC
from dataclasses import dataclass
from io import StringIO
from typing import Iterable, Mapping, Optional, Sequence

if typing.TYPE_CHECKING:
    from .deep_getter import GetterContext
    from .placeholders import Placeholder

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


@dataclass
class Trace:
    """Config Exception Trace Entry"""

    path: tuple[str | int, ...] | None = None
    placeholder: Optional["Placeholder"] = None
    file: str | None = None


class ConfigException(Exception):
    """Base class for Config Exceptions"""

    def __init__(
        self,
        *args: object,
        ctx: "GetterContext" = None,
        placeholder: "Placeholder" = None,
    ) -> None:
        super().__init__(*args)

        trace = []
        if ctx is not None:
            trace.append(Trace(ctx.cur_path(), placeholder, None))

        self.trace: list[Trace] = trace

    def __str__(self) -> str:
        out = StringIO(super().__str__())

        if self.trace:
            print(file=out)  # newline
            print("Config Trace:", file=out)  # newline

            for i, trace in enumerate(self.trace):
                print(file=out)  # newline
                print(f"{i:2d}: path={trace.path}", file=out)
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

PathType = str | int | Iterable[str | int]

DEFAULT = object()
