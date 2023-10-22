#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Package utilities
"""

from dataclasses import dataclass
import logging
from abc import ABC
import typing
from typing import Iterable, Mapping, Sequence, Optional

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
        placeholder: "Placeholder" = None
    ) -> None:
        super().__init__(*args)

        trace = []
        if ctx is not None:
            trace.append(Trace(ctx.cur_path(), placeholder, None))

        self.trace: list[Trace] = trace


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
