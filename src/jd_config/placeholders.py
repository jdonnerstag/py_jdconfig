#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""Manage everything related to placeholders, such as
```
  db_engine: '{ref: db.engine, innodb}'
```

Placeholders can only occur in yaml values. They are not allowed in keys.
And it must be a yaml *string* value, surrounded by quotes.
"""

import dataclasses
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from .utils import ConfigException, ContainerType

if TYPE_CHECKING:
    from .deep_getter import GetterContext

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


LoaderType = Callable[[str], Mapping]


@dataclass
class ImportPlaceholder(Placeholder):
    """Import Placeholder: '{import: <file>[, <replace=False>]}'"""

    file: str
    loader: Optional[LoaderType] = field(default=None, repr=False)
    # TODO Add an optional cache flag

    def __post_init__(self):
        assert self.file
        if isinstance(self.file, (str, Path)):
            if Path(self.file).is_absolute():
                logger.warning("Absolut import file path detected: '%s'", self.file)

    def resolve(self, getter, ctx: "GetterContext"):
        if hasattr(getter, "resolve") and callable(getter.resolve):
            file = getter.resolve(self.file, ctx)
        else:
            logger.warning("ImportPlaceholder: No resolver configured")

        assert (
            self.loader is not None
        ), "ImportPlaceholder: Bug. No file 'loader' configured"

        rtn = self.loader.load(file)

        if ctx.file_imports is None:
            ctx.file_imports = []
        fname = self.loader.files_loaded[-1]
        if fname in ctx.file_imports:
            raise ConfigException(f"Import file recursion detected: {ctx.file_imports}")
        ctx.file_imports.append(fname)

        # Update the default root object to resolve against.
        # Default for {ref:} is 'within the file'
        # Use {global:} to reference the absolut root.
        ctx.files.append(rtn)
        ctx.memo = None

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
        data = ctx.files[-1]
        new_ctx = dataclasses.replace(ctx)
        return self._resolve_inner(getter, new_ctx, data)

    def _resolve_inner(self, getter, ctx: "GetterContext", data):
        try:
            obj = getter.get(data, self.path, ctx=ctx)
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


ConfigFn = Callable[[], ContainerType]


@dataclass
class GlobalRefPlaceholder(RefPlaceholder):
    """Reference Placeholder: '{global: <path>[, <default>]}'

    ref and global are identical, except that the map they resolve
    against is different.
    """

    # The order of the arguments is: all the attributes from the parent(s)
    # class(es) first then those of the child class.
    root_cfg: Optional[ConfigFn] = field(default=None, repr=False)

    def resolve(self, getter, ctx: "GetterContext"):
        data = ctx.files[0]
        new_ctx = dataclasses.replace(ctx, files=[data])
        return self._resolve_inner(getter, new_ctx, data)


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
