#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Package utilities
"""

import logging
from abc import ABC
from typing import Iterable, Mapping, Sequence

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class ConfigException(Exception):
    """Base class for Config Exceptions"""


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
