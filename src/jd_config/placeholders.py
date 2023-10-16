#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Optional

from .utils import ConfigException

if TYPE_CHECKING:
    from .deep_getter_base import GetterContext

__parent__name__ = __name__.rpartition(".")[0]
logger = logging.getLogger(__parent__name__)


class PlaceholderException(ConfigException):
    """Placeholder exception"""


# pylint: disable=too-few-public-methods
class Placeholder(ABC):
    """A common base class for all Placeholders"""

    @abstractmethod
    def resolve(self, getter, ctx: "GetterContext"):
        """Resolve the placeholder"""


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'"""

    file: str | list

    def __post_init__(self):
        assert self.file
        if isinstance(self.file, (str, Path)):
            if Path(self.file).is_absolute():
                logger.warning("Absolut import file path detected: '%s'", self.file)

    def resolve(self, getter, ctx: "GetterContext"):
        # TODO It is not possible to recursively call get()
        assert hasattr(getter, "resolve")
        file = getter.resolve(self.file, ctx)
        rtn = getter.load(file)
        return rtn


@dataclass
class RefPlaceholder(Placeholder):
    """Reference Placeholder: '{ref: <path>[, <default>]}'"""

    path: str
    default_val: Any = None
    file_root: Optional[Mapping] = None

    def __post_init__(self):
        assert self.path

    def resolve(self, getter, ctx: "GetterContext"):
        try:
            obj = getter.get(ctx.root, self.path, _memo=ctx.memo)
            return obj
        except (
            KeyError,
            IndexError,
            ConfigException,
        ) as exc:  # pylint: disable=bare-except  # noqa: E722
            if self.default_val is not None:
                return obj

            if isinstance(exc, ConfigException):
                raise

            raise PlaceholderException(
                f"Failed to resolve RefPlaceholder: '{self.path}'"
            ) from exc


@dataclass
class GlobalRefPlaceholder(RefPlaceholder):
    """Reference Placeholder: '{global: <path>[, <default>]}'"""

    # TODO Not yet implemented. ref and global are identical, except
    # that the map they resolve against is different.


@dataclass
class EnvPlaceholder(Placeholder):
    """Environment Variable Placeholder: '{env: <env-var>[, <default>]}'"""

    env_var: str
    default_val: Any = None

    def __post_init__(self):
        assert self.env_var

    def resolve(self, *_, **__) -> str:
        value = os.environ.get(self.env_var, self.default_val)
        return value


@dataclass
class TimestampPlaceholder(Placeholder):
    """Replace yaml value with timestamp: '{timestamp: <format>}'"""

    format: str

    def __post_init__(self):
        assert self.format

    def resolve(self, *_, **__) -> str:
        now = datetime.now()
        value = now.strftime(self.format)
        return value
